#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import Counter
import sys

from framenetallreader import FNAllReader
from verbnetframe import VerbnetFrameOccurrence
from stats import stats_quality, display_stats, stats_data, stats_ambiguous_roles
import errorslog
from errorslog import log_debug_data, log_vn_missing, display_debug
from bootstrap import bootstrap_algorithm
from verbnetrestrictions import NoHashDefaultDict
import options
import argguesser
import roleextractor
import verbnetreader
import framematcher
import rolematcher
import probabilitymodel
import headwordextractor
import paths
import dumper


if __name__ == "__main__":
    print("Loading VerbNet...")
    frames_for_verb, verbnet_classes = verbnetreader.init_verbnet(paths.VERBNET_PATH)

    print("Loading FrameNet and VerbNet roles mappings...")
    role_matcher = rolematcher.VnFnRoleMatcher(paths.VNFN_MATCHING)

    model = probabilitymodel.ProbabilityModel(verbnet_classes, 0)
    hw_extractor = headwordextractor.HeadWordExtractor()

    all_annotated_frames = []
    all_vn_frames = []

    annotation_list, parsed_conll_list = FNAllReader.fulltext_annotations(), FNAllReader.fulltext_parses()

    print("Loading FrameNet annotations and frame matching...")
    for annotation_file, parsed_conll_file in zip(annotation_list, parsed_conll_list):
        annotated_frames = []
        vn_frames = []

        if options.gold_args:
            #
            # Load gold arguments
            #
            fn_reader = FNAllReader(
                core_args_only=options.core_args_only)

            for frame in fn_reader.iter_frames(annotation_file, parsed_conll_file):
                stats_data["args"] += len(frame.args)
                stats_data["args_instanciated"] += len(
                    [x for x in frame.args if x.instanciated])
                stats_data["frames"] += 1
                
                if not frame.predicate.lemma in frames_for_verb:
                    log_vn_missing(frame)
                    continue

                stats_data["frames_with_predicate_in_verbnet"] += 1

                annotated_frames.append(frame)
                vn_frames.append(VerbnetFrameOccurrence.build_from_frame(frame))

            stats_data["files"] += fn_reader.stats["files"]
        else:
            #
            # Argument identification
            #
            arg_guesser = argguesser.ArgGuesser(verbnet_classes)
            
            frame_instances = list(arg_guesser.frame_instances_from_file(parsed_conll_file))
            new_annotated_frames = roleextractor.fill_gold_roles(frame_instances,
                annotation_file, parsed_conll_file, verbnet_classes,
                role_matcher)
            
            for frame in new_annotated_frames:
                annotated_frames.append(frame)
                vn_frames.append(VerbnetFrameOccurrence.build_from_frame(frame))


        # Extract arguments headwords
        hw_extractor.compute_all_headwords(annotated_frames, vn_frames)

        #
        # Frame matching
        #
        all_matcher = []
        data_restr = NoHashDefaultDict(lambda : Counter())
        assert len(annotated_frames) == len(vn_frames)
        for good_frame, frame_occurrence in zip(annotated_frames, vn_frames):
            num_instanciated = len([x for x in good_frame.args if x.instanciated])
            predicate = good_frame.predicate.lemma

            if good_frame.arg_annotated:
                stats_data["args_kept"] += num_instanciated

            stats_ambiguous_roles(good_frame, num_instanciated,
                role_matcher, verbnet_classes)

            # Check that FrameNet frame slots have been mapped to VerbNet-style slots
            if frame_occurrence.num_slots == 0:
                errorslog.log_frame_without_slot(good_frame, frame_occurrence)
                continue

            matcher = framematcher.FrameMatcher(frame_occurrence, options.matching_algorithm)
            all_matcher.append(matcher)

            errorslog.log_frame_with_slot(good_frame, frame_occurrence)
            stats_data["frames_mapped"] += 1

            # Actual frame matching
            for verbnet_frame in frames_for_verb[predicate]:
                if options.passive and good_frame.passive:
                    try:
                        for passivized_frame in verbnet_frame.passivize():
                            matcher.new_match(passivized_frame)
                    except:
                        continue
                else:
                    matcher.new_match(verbnet_frame)

            frame_occurrence.roles = matcher.possible_distribs()

            # Update semantic restrictions data
            for word, restr in matcher.get_matched_restrictions().items():
                if restr.logical_rel == "AND":
                    for subrestr in restr.children:
                        data_restr[subrestr].update([word])
                else:
                    data_restr[restr].update([word])

            # Update probability model
            vnclass = model.add_data_vnclass(matcher)
            if not options.bootstrap:
                for roles, slot_type, prep in zip(
                    frame_occurrence.roles, frame_occurrence.slot_types, frame_occurrence.slot_preps
                ):
                    if len(roles) == 1:
                        model.add_data(slot_type, next(iter(roles)), prep, predicate, vnclass)

            if options.debug and set() in frame_occurrence.roles:
                log_debug_data(good_frame, frame_occurrence, matcher, frame_occurrence.roles, verbnet_classes)

        if options.dump:
            dumper.add_data_frame_matching(annotated_frames, vn_frames,
                role_matcher, verbnet_classes,
                frames_for_verb, options.matching_algorithm)

        if options.semrestr:
            for matcher in all_matcher:
                matcher.handle_semantic_restrictions(data_restr)
                matcher.frame_occurrence.roles = matcher.possible_distribs()

            #stats_quality(annotated_frames, vn_frames, role_matcher, verbnet_classes, options.gold_args)
            #display_stats(options.gold_args)

        all_vn_frames.extend(vn_frames)
        all_annotated_frames.extend(annotated_frames)

    print("\n\n## Frame matching stats")
    stats_quality(all_annotated_frames, all_vn_frames, role_matcher, verbnet_classes, options.gold_args)
    display_stats(options.gold_args)

    print("Applying probabilty model...")
    for annotation_file, parsed_conll_file in zip(annotation_list, parsed_conll_list):
        #
        # Probability model
        #
        if options.bootstrap:
            # Compute headwords classes
            hw_extractor.compute_word_classes()

            bootstrap_algorithm(all_vn_frames, model, hw_extractor, verbnet_classes)
        else:
            for frame in all_vn_frames:
                for i, roles in enumerate(frame.roles):
                    if len(frame.roles[i]) > 1:
                        new_role = model.best_role(
                            frame.roles[i], frame.slot_types[i], frame.slot_preps[i],
                            frame.predicate, options.probability_model)
                        if new_role != None:
                            frame.roles[i] = set([new_role])

        if options.dump:
            dumper.add_data_prob_model(all_annotated_frames, all_vn_frames, role_matcher, verbnet_classes)
            dumper.dump(options.dump_file)

        if options.debug:
            display_debug(options.n_debug)

    print("\n\n## Final stats")
    stats_quality(all_annotated_frames, all_vn_frames, role_matcher, verbnet_classes, options.gold_args)
    display_stats(options.gold_args)
