#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Frames, arguments and predicates."""

class Frame:
    """A frame extracted from the corpus 
    
    :var sentence: Sentence in which the frame appears
    :var predicate: Predicate object representing the frame's predicate
    :var args: Arg list containing the predicate's arguments
    
    """
    
    def __init__(self, sentence, predicate, args):
        self.sentence = sentence
        self.predicate = predicate
        self.args = args
        self.args.sort()
        
    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
            self.sentence == other.sentence and
            self.predicate == other.predicate and
            self.args == other.args)
        
class Arg:

    """An argument of a frame 

    :var begin: integer, position of the argument's first character in the sentence
    :var end: integer, position of the argument's last character in the sentence
    :var text: string containing the argument's text
    :var role: string containing the argument's role
    :var instanciated: boolean that marks wether the argument is instanciated
    
    """
    
    def __init__(self, begin, end, text, role, instanciated, phrase_type):
        self.begin = begin
        self.end = end
        self.text = text
        self.role = role
        self.instanciated = instanciated
        self.phrase_type = phrase_type
        
    def __eq__(self, other):
        return (isinstance(other, self.__class__)  and
            ((self.begin == other.begin and self.end == other.end) or
                (self.instanciated == False and other.instanciated == False)) and
            self.role == other.role and
            self.phrase_type == other.phrase_type)
            
    def __cmp__(self, other):
        if not self.instanciated:
            if other.instanciated: return 1
            if self.role < other.role: return -1
            if self.role > other.role: return 1
            return 0
        if not other.instanciated: return -1
        if self.begin < other.begin: return -1
        if self.begin > other.begin: return 1
        return 0
        
    def __lt__(self, other):
        return self.__cmp__(other) < 0
        
    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0
    
class Predicate:

    """A frame's predicate 
    
    :var begin: integer, position of the predicate's first character in the sentence
    :var end: integer, position of the predicate's last character in the sentence
    :var text: string containing the predicate's text
    
    """
    
    def __init__(self, begin, end, text, lemma):
        self.begin = begin
        self.end = end
        self.text = text
        self.lemma = lemma
        
    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
            self.begin == other.begin and
            self.end == other.end and
            self.lemma == other.lemma)

