#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Map FrameNet and VerbNet roles """

import xml.etree.ElementTree as ET

from collections import defaultdict


# VN roles given by table 2 of http://verbs.colorado.edu/~mpalmer/projects/verbnet.html
vn_roles_list = [
    "Actor", "Agent", "Asset", "Attribute", "Beneficiary", "Cause",
    "Co-Agent", "Co-Patient", "Co-Theme",  # Not in the original list
    "Location", "Destination", "Source", "Experiencer", "Extent",
    "Instrument", "Material", "Product", "Patient", "Predicate",
    "Recipient", "Stimulus", "Theme", "Time", "Topic"]

# Added roles
vn_roles_additionnal = ["Goal", "Initial_Location", "Pivot", "Result",
    "Trajectory", "Value"]

# List of VN roles that won't trigger an error in unit tests
authorised_roles = vn_roles_list + vn_roles_additionnal


class RoleMatchingError(Exception):
    """ Missing data to compare a vn and a fn role

    :var msg: str, a message detailing what is missing
    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return ("Error : {}".format(self.msg))


class VnFnRoleMatcher():
    """Reads the mapping between VN and FN roles, and can then be used to compare them

    :var fn_roles: data structure used to store the mapping between VN and FN roles
    :var issues: used to store statistics about the problem encoutered
    """

    def __init__(self, path):
        # 4-dimensions matrix :
        # self.fn_roles[fn_role][fn_frame][vn_class][i] is the
        # i-th possible VN role associated to fn_role for the frame fn_frame
        # and a verb in vn_class.
        self.fn_roles = {}

        self._build_mapping(path)

    def _build_mapping(self, path):
        root = ET.ElementTree(file=str(path))

        for mapping in root.getroot():
            vn_class = mapping.attrib["class"]
            fn_frame = mapping.attrib["fnframe"]

            mapping_as_dict = {}

            for role in mapping.findall("roles/role"):
                vn_role = role.attrib["vnrole"]
                fn_role = role.attrib["fnrole"]

                vn_role = self._handle_co_roles(vn_role)

                mapping_as_dict[fn_role] = vn_role

                self._add_relation(
                    fn_role, vn_role,
                    fn_frame, vn_class)

    def _handle_co_roles(self, vn_role):
        if vn_role[-1] == "1":
            return vn_role[0:-1]
        if vn_role[-1] == "2":
            return "Co-"+vn_role[0:-1]
        return vn_role

    def _add_relation(self, fn_role, vn_role, fn_frame, vn_class):
        if fn_role not in self.fn_roles:
            self.fn_roles[fn_role] = {"all": set()}
        if fn_frame not in self.fn_roles[fn_role]:
            self.fn_roles[fn_role][fn_frame] = {"all": set()}
        if vn_class not in self.fn_roles[fn_role][fn_frame]:
            self.fn_roles[fn_role][fn_frame][vn_class] = set()

        self.fn_roles[fn_role]["all"].add(vn_role)
        self.fn_roles[fn_role][fn_frame]["all"].add(vn_role)
        self.fn_roles[fn_role][fn_frame][vn_class].add(vn_role)

    def possible_vn_roles(self, fn_role, fn_frame=None, vn_classes=None):
        """Returns the set of VN roles that can be mapped to a FN role in a given context

        :param fn_role: The FrameNet role.
        :type fn_role: str.
        :parma vn_role: The VerbNet role.
        :type vn_role: str.
        :param fn_frame: The FrameNet frame in which the roles have to be mapped.
        :type fn_frame: str.
        :param vn_classes: A list of VerbNet classes for which the roles have to be mapped.
        :type vn_classes: str List.
        :returns: str List -- The list of VN roles
        """

        if fn_role not in self.fn_roles:
            raise RoleMatchingError(
                "{} role does not seem"
                " to exist".format(fn_role))
        if fn_frame is None and vn_classes is None:
            return self.fn_roles[fn_role]["all"]

        if fn_frame is not None and fn_frame not in self.fn_roles[fn_role]:
            raise RoleMatchingError(
                "{} role does not seem"
                " to belong to frame {}".format(fn_role, fn_frame))
        if vn_classes is None:
            return self.fn_roles[fn_role][fn_frame]["all"]

        if fn_frame is None:
            frames = list(self.fn_roles[fn_role].keys())
            frames.remove("all")
        else:
            frames = [fn_frame]

        vn_roles = set()

        for vn_class in vn_classes:
            # Use the format of the vn/fn mapping
            vn_class = "-".join(vn_class.split('-')[1:])
            for frame in frames:
                while True:
                    if vn_class in self.fn_roles[fn_role][frame]:
                        vn_roles = vn_roles.union(self.fn_roles[fn_role][frame][vn_class])
                        break

                    position = max(vn_class.rfind("-"), vn_class.rfind("."))
                    if position == -1:
                        break

                    vn_class = vn_class[0:position]

        if vn_roles == set():
            # We don't have the mapping for any of the VN class provided in vn_classes
            raise RoleMatchingError(
                "None of the given VerbNet classes ({}) were corresponding to"
                " {} role and frame {}".format(vn_class, fn_role, fn_frame))

        return vn_roles

    def build_frames_vnclasses_mapping(self):
        """ Builds a mapping between framenet frames and associated verbnet classes """
        self.fn_frames = defaultdict(lambda: set())
        for fn_role in self.fn_roles:
            if fn_role == "all":
                continue
            for fn_frame in self.fn_roles[fn_role]:
                if fn_frame == "all":
                    continue
                for vn_class in self.fn_roles[fn_role][fn_frame]:
                    if vn_class == "all":
                        continue
                    self.fn_frames[fn_frame].add(vn_class)
