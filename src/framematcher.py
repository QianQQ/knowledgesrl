#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Match VerbnetFrameOccurrence to appropriate VerbNetOfficialFrame syntax

Based on the 2004 Swier & Stevenson paper: Unsupervised Semantic Role Labeling.

The way frame matching works in Swier&Stevenson 2004 paper is not completely
specified: what happens when VerbNet frame is longer than FrameNet's frame?

Currently, we don't extract any slot when a non-match appears: while it can
make sense to omit objects at the end, it doesn't to omit at the beginning and
take at the end: this could result in a totally different syntactic
construction. But I could be wrong!

For example, if you have in FrameNet "NP V with NP", and VerbNet contains "NP V
NP with NP", what do you do? We decided, for now, to only match the syntactic
subject.
"""

import options
import logging
logger = logging.getLogger(__name__)
logger.setLevel(options.Options.loglevel)

from verbnetframe import ComputeSlotTypeMixin, VerbnetFrameOccurrence
from verbnetrestrictions import VNRestriction


class FrameMatcher():
    """Handle frame matching for a given frame that we want to annotate.

    :var frame_occurrence: VerbnetFrameOccurrence -- The frame to annotate
    :var algo: str -- The algorithm that we want to use

    """

    def __init__(self, frame_occurrence, algo):
        self.frame_occurrence = frame_occurrence
        self.algo = algo

    def restrict_headwords_with_wordnet(self):
        """Keep only frames for which the selectional restrictions are matched according to WordNet"""
        one_role_compatible_match_list = []
        for i, match in enumerate(self.frame_occurrence.best_matches):
            for slot1, slot2 in enumerate(match['slot_assocs']):
                if slot2 is None:
                    continue

                headword = self.frame_occurrence.headwords[slot1]['content_headword']
                selrestr = match['vnframe'].selrestrs()[slot2]
                headword_matches_selrestr = selrestr.matches_to_headword(headword)
                if headword_matches_selrestr:
                    one_role_compatible_match_list.append(i)

        for i, match in enumerate(self.frame_occurrence.best_matches):
            if i not in one_role_compatible_match_list:
                self.frame_occurrence.remove_match(match)

    def handle_semantic_restrictions(self, restr_data):
        """Keep only frames for which the syntactic restriction are
        the best matched

        :param restr_data: The gathered relations between restrictions and words
        :type restr_data: (VNRestriction -> (str Counter)) NoHashDefaultDict

        """
        scores = [self.frame_semantic_score(match, restr_data) for match in self.frame_occurrence.best_matches]

        for match, score in zip(self.frame_occurrence.best_matches, scores):
            if score < max(scores):
                self.frame_occurrence.remove_match(match)

    def frame_semantic_score(self, match, semantic_data):
        """For a given frame from VerbNet, compute a semantic score between
        this frame and the headwords of the real frame associated with
        FrameMatcher.

        :param match: The match: frame and the associated mapping
        :type frame_data: ('vnframe', 'slot_assocs') dict
        :param semantic_data: The gathered relations between restrictions and words
        :type semantic_data: (VNRestriction -> (str Counter)) NoHashDefaultDict

        """

        score = 0
        for slot1, slot2 in enumerate(match['slot_assocs']):
            if slot2 is None:
                continue
            if slot2 >= match['vnframe'].num_slots:
                continue

            word = self.frame_occurrence.headwords[slot1]['top_headword']
            restr = match['vnframe'].selrestrs()[slot2]
            score += restr.match_score(word, semantic_data)

        return score

    def get_matched_restrictions(self):
        """Returns the list of restrictions for which we know a given word was
        a match. Only headwords of arguments for which we attributed exactly
        one possible role are taken into account. The restriction associated to
        them is the OR of restrictions associated to this slot in every
        possible frame.

        :returns: VNRestriction Dict -- a mapping between head words and the restriction they match
        """
        for i, role in enumerate(self.frame_occurrence.roles):
            if role is None or len(role) != 1:
                continue

            restr = VNRestriction.build_empty()
            for match in self.frame_occurrence.best_matches:
                if match['slot_assocs'][i] is None:
                    continue
                elif match['slot_assocs'][i] >= match['vnframe'].num_slots:
                    continue
                elif match['vnframe'].selrestrs()[match['slot_assocs'][i]] is None:
                    continue
                restr = VNRestriction.build_or(
                    restr,
                    match['vnframe'].selrestrs()[match['slot_assocs'][i]])

            yield i, restr

    @staticmethod
    def _is_a_match(frame_occurrence_part, official_frame_part):
        """Tell wether two elements can be considered as a match

        frame_occurrence_part is a seen element, while official_frame_elem can
        contain a set of possible elements, such as prepositions
        """

        if isinstance(official_frame_part['elem'], set):
            return frame_occurrence_part['elem'] in official_frame_part['elem']
        else:
            return frame_occurrence_part['elem'] == official_frame_part['elem']

    def _matching_baseline(self, verbnet_frame, slots_associations):
        """ Matching algorithm that is the closest to the article's method """
        # As slots are not attributed in order, we need to keep a list
        # of the slots that have not been attributed yet
        available_slots = []
        num_match = 0

        for i, x in enumerate(verbnet_frame.slot_types):
            available_slots.append(
                {"slot_type": x, "pos": i, "prep": verbnet_frame.slot_preps[i]}
            )

        for slot_pos, slot_type in enumerate(self.frame_occurrence.slot_types):
            # For every slot, try to find a matching slot in available_slots
            i, matching_slot = -1, -1

            for test_slot_data in available_slots:
                # Could have used enumerate, but it looks better like this
                # as i is used after the loop
                i += 1

                # We want a slot that has the same type and the same prep
                # (or a list slot preps containing our preposition)
                if test_slot_data["slot_type"] != slot_type:
                    continue

                if (slot_type == ComputeSlotTypeMixin.slot_types["prep_object"] and
                    not FrameMatcher._is_a_match(
                        {'elem': self.frame_occurrence.slot_preps[slot_pos]},
                        {'elem': test_slot_data["prep"]})):
                    continue

                matching_slot = test_slot_data["pos"]
                break  # Stop at the first good slot we find

            if matching_slot != -1:
                del available_slots[i]  # Slot i has been attributed
                # TODO? we need to check that enough roles were given in VerbNet
                if verbnet_frame.num_slots > matching_slot:
                    slots_associations[slot_pos] = matching_slot

                num_match += 1
        return num_match, slots_associations

    def _matching_sync_predicates(self, verbnet_frame, slots_associations):
        """ Stop the algorithm at the first mismatch encountered after the verb,
        restart at the verb's position if a mismatch is encountered before the
        verb """

        num_match = 0
        i, j = 0, 0
        index_v_in_frame_occurrence = self.frame_occurrence.structure.index({'elem': 'V'})
        index_v_in_official_frame = verbnet_frame.syntax.index({'elem': 'V'})
        slot_1, slot_2 = 0, 0
        num_slots_before_v_in_frame_occurrence = 0
        num_slots_before_v_in_official_frame = 0

        for part in self.frame_occurrence.structure:
            if VerbnetFrameOccurrence._is_a_slot(part):
                num_slots_before_v_in_frame_occurrence += 1
            elif part['elem'] == "V":
                break

        for part in verbnet_frame.syntax:
            if 'role' in part:
                num_slots_before_v_in_official_frame += 1
            elif part['elem'] == "V":
                break

        while i < len(self.frame_occurrence.structure) and j < len(verbnet_frame.syntax):
            occured_part = self.frame_occurrence.structure[i]
            official_part = verbnet_frame.syntax[j]

            if FrameMatcher._is_a_match(occured_part, official_part):
                if VerbnetFrameOccurrence._is_a_slot(occured_part):
                    num_match += 1
                    # TODO this is probably fixed with the SYNTAX-based VN reader
                    # verbnet_frame can have more syntax than roles.This will
                    # for instance happen in the "NP V NP S_INF" syntax of
                    # want-32.1, where S_INF is given no role since it's part
                    # of the NP
                    if slot_2 < verbnet_frame.num_slots:
                        slots_associations[slot_1] = slot_2
                        slot_1, slot_2 = slot_1 + 1, slot_2 + 1
            # no match, but not seen the verb everywhere yet
            elif i < index_v_in_frame_occurrence or j < index_v_in_official_frame:
                # If we have not encountered the verb yet, we continue the matching
                # with everything that follows the verb
                # This is for instance to prevent a "NP NP V" construct
                # from interrupting the matching early
                i, j = index_v_in_frame_occurrence, index_v_in_official_frame
                slot_1 = num_slots_before_v_in_frame_occurrence
                slot_2 = num_slots_before_v_in_official_frame
            else:
                break

            i, j = i + 1, j + 1

        return num_match, slots_associations

    def _matching_stop_on_fail(self, verbnet_frame, slots_associations):
        """ Stop the algorithm at the first mismatch encountered """
        num_match = 0
        for occured_part, official_part in zip(self.frame_occurrence.structure, verbnet_frame.syntax):
            if FrameMatcher._is_a_match(occured_part, official_part):
                if VerbnetFrameOccurrence._is_a_slot(occured_part):
                    num_match += 1
                    if num_match - 1 < verbnet_frame.num_slots:
                        slots_associations[num_match - 1] = num_match - 1
            else:
                break

        return num_match, slots_associations

    def perform_frame_matching(self, official_frames_to_be_matched):
        """Compute the matching score and update the possible roles distribs

        :param official_frames_to_be_matched: frames to test.
        :type official_frames_to_be_matched: VerbnetOfficialFrame list.

        """
        logger.debug('perform_frame_matching with algo {}'.format(self.algo))
        best_score = 0
        for verbnet_frame in official_frames_to_be_matched:
            slots_associations = [None for x in range(self.frame_occurrence.num_slots)]

            # Consider 'that' as optional in english, eg.:
            # Tell him that S --> Tell him S
            import copy
            if verbnet_frame.has('that') and {'elem': 'that'} not in self.frame_occurrence.structure:
                verbnet_frame = copy.deepcopy(verbnet_frame)
                verbnet_frame.remove('that')

            if self.algo == "baseline":
                matching_function = self._matching_baseline
            elif self.algo == "sync_predicates":
                matching_function = self._matching_sync_predicates
            elif self.algo == "stop_on_fail":
                matching_function = self._matching_stop_on_fail
            else:
                raise Exception("Unknown matching algorithm : {}".format(self.algo))

            num_match, slots_associations = matching_function(verbnet_frame, slots_associations)
            logger.debug('Match result with {} : num_match={} slots_associations={}'.format(verbnet_frame, num_match, slots_associations))
                
            # Score computation
            ratio_1 = num_match / self.frame_occurrence.num_slots
            if verbnet_frame.num_slots == 0:
                ratio_2 = 1
            else:
                ratio_2 = num_match / verbnet_frame.num_slots
                
            score = int(100 * (ratio_1 + ratio_2))
            logger.debug('Score computation current best={} ; {} {} {} ; {}'
                .format(best_score, num_match, self.frame_occurrence.num_slots, verbnet_frame.num_slots, score))
            
            
            # This frame is better than any previous one: reset everything
            if score > best_score:
                self.frame_occurrence.remove_all_matches()
                best_score = score

            # This frame is at least as good as the others: add its data
            if score >= best_score:
                self.frame_occurrence.add_match({'vnframe': verbnet_frame, 'slot_assocs': slots_associations}, score)

        # Used to test the function
        return best_score
