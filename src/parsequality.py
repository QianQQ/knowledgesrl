#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from framenetreader import FulltextReader
from conllreader import SyntacticTreeBuilder
import glob
import os
import options


def get_trees(filename):
    # get data from parse trees
    tree_list = []
    with open(str(filename)) as conll_file:
        conll_tree = ""
        for l in conll_file.readlines():
            if l != "\n":
                conll_tree += l
            else:
                trees_for_sentence = SyntacticTreeBuilder(conll_tree).tree_list
                if not len(trees_for_sentence) == 1:
                    print('{} trees in one sentence of {}'.format(len(trees_for_sentence), filename))

                tree_list.append(trees_for_sentence[0])
                conll_tree = ""

    return tree_list


if __name__ == '__main__':
    correct, partial, total = 0, 0, 0

    # get data from FrameNet arguments
    for annotation_file, parsed_conll_file in zip(options.fulltext_annotations, options.fulltext_parses):
        reader = FulltextReader(annotation_file)
        tree_list = get_trees(parsed_conll_file)

        # for each argument, see if it is in a parse tree. if yes +1
        for frame in reader.frames:
            print('.', end='', flush=True)
            frame_text = " ".join([frame.get_word(w) for w in frame.words])
            for tree in tree_list:
                if tree.flat().lower() == frame_text.lower():
                    for arg in frame.args:
                        if arg.text != "":
                            total += 1
                            score = tree._closest_match_as_node_lcs(arg)[0]
                            partial += score
                            if score == 1:
                                correct += 1
                    break
        print()
        
    print("Correct: {:.02f} - Partial {:.02f} (out of {} args)".format(correct/total, partial/total, total))
