#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Extract headwords of arguments and determine their WordNet class"""

import os
import sys
import unittest
import random
import pickle
import getopt

from framenetparsedreader import FNParsedReader
import framenetreader
import options


class HeadWordExtractor(FNParsedReader):
    """This object usess syntactic annotations of FrameNet to retrieve the headwords of
    arguments, and attributes them a WordNet class.
        
    :var word_classes: str Dict -- Retrieved WordNet classes of identified headwords.
    :var special_classes: str Dict -- Special classes for non noun headwords.
    :var words: str Set -- Set of words for which we need to compute the WordNet class.
        
    """
    
    def __init__(self, path):
        FNParsedReader.__init__(self, path)
        self.word_classes = {}
        self.special_classes = {}
        self.words = set()
    
    def compute_word_classes(self):
        """Fills word_classes by asking the Python2 script which can talk to nltk."""
        with open("temp_wordlist", "wb") as picklefile:
            pickle.dump(self.words, picklefile, 2)
        
        os.system("python2.7 wordclassesloader.py")
        
        with open("temp_wordclasses", "rb") as picklefile:
            self.word_classes.update(pickle.load(picklefile))
            
        os.remove("temp_wordlist")
        os.remove("temp_wordclasses")
        
        self.word_classes.update(self.special_classes)
    
    def headword(self, arg_text):
        """Returns the headword of an argument, assuming the proper sentence have
        already been selected.
        
        :param arg_text: The argument.
        :type arg_text: str.
        :returns: str -- The headword
        
        """
        if self.tree == None: return ""
        
        word, pos = self._get_headword(arg_text.lower())
        
        if pos == "PRP": self.special_classes[word] = "pronoun"
        elif pos == "NNP": self.special_classes[word] = "proper_noun"
        else: self.words.add(word)

        return word
        
    def best_node(self, arg_text):
        """Looks for the closest match of an argument in the syntactic tree.
        This method is only here for debug purposes.
        
        :param arg_text: The argument.
        :type arg_text: str.
        :returns: SyntacticTreeNode -- The nodes which contents match arg_text the best
        
        """
        if self.tree == None: return None
        return self.tree.closest_match_as_node(arg_text)

    def get_class(self, word):
        """Looks for the WordNet class of a word and returns it.
        
        :param word: The word
        :type word: str.
        :returns: str -- The class of the word or "unknown" if it was not found
        """
        if word in self.word_classes:
            return self.word_classes[word]
        return "unknown"
    
    def compute_all_headwords(self, frames, vn_frames):
        """ Fills frame data with the headwords of the arguments.
        
        :param frames: The FrameNet frames as returned by a FrameNetReader.
        :type frames: Frame List.
        :param vn_frames: The frames that we have to complete with headwords.
        :type vn_frames: VerbnetFrame List.
        """
        
        for frame, vn_frame in zip(frames, vn_frames):
            self.tree = frame.tree
            
            vn_frame.headwords = [
                self.headword(x.text) for x in frame.args if x.instanciated]
        
    def _get_headword(self, arg_text):
        node = self.tree.closest_match_as_node(arg_text)
        return node.word, node.pos
  
class HeadWordExtractorTest(unittest.TestCase):
    bad_files = [
            "ANC__110CYL070.xml", "C-4__C-4Text.xml",
            "NTI__BWTutorial_chapter1.xml", "NTI__LibyaCountry1.xml",
            "NTI__NorthKorea_Introduction.xml"]
    bad_sentences = [
            ("LUCorpus-v0.3__sw2025-ms98-a-trans.ascii-1-NEW.xml", 9),
            ("NTI__Iran_Chemical.xml", 6),
            ("NTI__Iran_Chemical.xml", 62),
            ("NTI__Iran_Nuclear.xml", 5),
            ("NTI__Iran_Nuclear.xml", 49),
            ("NTI__Iran_Nuclear.xml", 68),
            ("NTI__Iran_Nuclear.xml", 82),
            ("PropBank__ElectionVictory.xml", 5),
            ("PropBank__ElectionVictory.xml", 9),
            ("PropBank__LomaPrieta.xml", 18)]
            
    def test_classes(self):
        filename = "ANC__110CYL067"
        extractor = HeadWordExtractor(options.framenet_parsed)
        extractor.load_file(filename+".conll")

        reader = framenetreader.FulltextReader(options.fulltext_corpus+filename+".xml", False)

        for frame in reader.frames:
            extractor.select_sentence(frame.sentence_id)
            for arg in frame.args:
                extractor.headword(arg.text)

        extractor.words.add("abcde")
        extractor.compute_word_classes()
        self.assertEqual(extractor.get_class("soda"), "physical_entity.n.01")
        self.assertEqual(extractor.get_class("i"), "pronoun")
        
        # get_class should return "unknown" for word that were not resolved by
        # the nltk script or that were never encountered
        
        self.assertEqual(extractor.get_class("abcde"), "unknown")
        self.assertEqual(extractor.get_class("fghij"), "unknown")

    def sample_args(self, num_sample = 10):
        """Not a unit test. Returns a random sample of argument/node/headword to help.
        
        :param num_sample: The requested number of results
        :type num_sample: int
        :returns: (str, str, str) List -- Some examples of (arg, best_node_text, headword)
        """
        extractor = HeadWordExtractor(options.framenet_parsed)

        sample = []
        for filename in sorted(os.listdir(options.fulltext_corpus)):
            if not filename[-4:] == ".xml": continue

            if filename in self.bad_files: continue
            
            print(filename, file=sys.stderr)
            
            extractor.load_file(filename)
            
            reader = framenetreader.FulltextReader(options.fulltext_corpus+filename, False)
            previous_sentence = 0

            for frame in reader.frames:
                if (filename, frame.sentence_id) in self.bad_sentences: continue
   
                if frame.sentence_id != previous_sentence:
                    extractor.select_sentence(frame.sentence_id)
                
                for arg in frame.args:
                    if not arg.instanciated: continue
                    node = extractor.best_node(arg.text)
                    sample.append((arg.text, node.flat(), node.word))
                
                previous_sentence = frame.sentence_id
                
        random.shuffle(sample)
        return sample[0:num_sample]
    
    def test_1(self):
        filename = "ANC__110CYL067"
        extractor = HeadWordExtractor(options.framenet_parsed)
        extractor.load_file(filename+".conll")

        reader = framenetreader.FulltextReader(options.fulltext_corpus+filename+".xml", False)

        frame = reader.frames[1]
        extractor.select_sentence(frame.sentence_id)
        self.assertTrue(extractor.headword(frame.args[0].text) == "you")
              
        frame = reader.frames[0]
        self.assertTrue(extractor.headword(frame.args[0].text) == "contribution")

if __name__ == "__main__":
    # The -s option makes the script display some examples of results
    # or write them in a file using pickle
    cli_options = getopt.getopt(sys.argv[1:], "s:", [])
    num_sample = 0
    filename = ""
    
    for opt, value in cli_options[0]:
        if opt == "-s":
            if len(cli_options[1]) >= 1:
                filename = cli_options[1][0]
            num_sample = int(value)
        
    if num_sample > 0:
        tester = HeadWordExtractorTest()
        result = tester.sample_args(num_sample)
        if filename == "":
            for exemple in result:
                print("{}\n{}\n{}\n".format(exemple[0], exemple[1], exemple[2]))
        else:
            with open(filename, "wb") as picklefile:
                pickle.dump(result, picklefile)
    else:
        unittest.main()
