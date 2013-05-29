#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Reads the files containing the syntactic parser output"""

import framenetreader
from conllreader import SyntacticTreeBuilder
import unittest
import paths
import os
import sys

class FNParsedReader:
    """A simple object that can read the syntactic parser output and
    build the corresponding syntactic trees.
    
    :var annotation_path: str -- The path to the annotated corpus.
    :var sentences_data: str List -- The parser output for each sentence in the current file.
    :var sentence_id: int -- The id of the current sentence (starting at 1 for the first sentence in the file).
    :var filename: str -- The name of the current file.
    :var tree: SyntacticTreeNode -- The tree corresponding to the current sentence.
    """
    
    def __init__(self, path):
        self.annotations_path = path
        self.sentences_data = []
        self.sentence_id = 0
        self.filename = None
        self.tree = None

    def load_file(self, filename):
        """Set the current file to filename, and fill sentences_data
        accordingly. Not affected by newlines at the end of the file.
        
        :param filename: The file to load.
        :type filename: str.
        :returns: boolean -- True if the file was correctly loaded, False otherwise.
        """
        path = self.annotations_path + filename.replace(".xml", ".conll")
        
        if not os.path.exists(path):
            self.tree = None
            self.sentences_data = []
            return False
            
        with open(path) as content:
            self.sentences_data = content.read().split("\n\n")
            if self.sentences_data[len(self.sentences_data) - 1] == "":
                del self.sentences_data[len(self.sentences_data) - 1]
        
        self.filename=filename
            
        return True
        
    def select_sentence(self, sentence_id):
        """Change the current sentence and rebuild the current tree accordingly.
        
        :param sentence_id: The id of the sentence to load.
        :type sentence_id: int.
        :returns: boolean -- True if the sentence was correctly loaded, False otherwise.
        """
        if len(self.sentences_data) < sentence_id:
            self.tree = None
            return False
            
        sentence = self.sentences_data[sentence_id - 1]
        self.tree = SyntacticTreeBuilder(sentence).build_syntactic_tree()

        self.sentence_id = sentence_id

        return True
        
    def current_sentence(self):
        """Compute the text of the current sentence and returns it."""
        if self.tree == None: return ""
        return self.tree.flat()

  
class FNParsedReaderTest(unittest.TestCase):
    def comp(self, original, parsed):
        return all(
            [x == y or y == "<num>" for x,y in zip(original.split(), parsed.split())]
        )

    # List of sentences and files for which the test would fail
    # because of mistakes in the parser output
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
            
    def test_sentences_match(self, num_sample = 0):
        print("Checking FrameNetParsedReader")
        extractor = FNParsedReader(paths.FRAMENET_PARSED)

        for filename in sorted(os.listdir(paths.FRAMENET_FULLTEXT)):
            if not filename[-4:] == ".xml": continue

            if filename in self.bad_files: continue
            
            print(".", file=sys.stderr, end="")
            sys.stderr.flush()
            
            extractor.load_file(filename)
            
            reader = framenetreader.FulltextReader(paths.FRAMENET_FULLTEXT+filename, False)
            previous_sentence = 0

            for frame in reader.frames:
                if (filename, frame.sentence_id) in self.bad_sentences: continue
   
                if frame.sentence_id != previous_sentence:
                    extractor.select_sentence(frame.sentence_id)
                
                self.assertTrue(self.comp(frame.sentence, extractor.current_sentence()))
                previous_sentence = frame.sentence_id

if __name__ == "__main__":
    unittest.main()