# -*- coding: utf-8 -*-

# Copyright (c) 2015 Pierre Parrend
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Created on 8 janv. 2015

@author: Pierre.Parrend
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import range
from builtins import object
from past.utils import old_div

from archan.dsm import DesignStructureMatrix
from archan.errors import ArchanError


class Archan(object):
    """Architecture analyser class.
    """

    def __init__(self):
        self.check_complete_mediation_implemented = True
        self.check_economy_of_mechanism_implemented = True
        self.check_separation_of_privileges_implemented = False
        self.check_least_privileges_implemented = False
        self.check_least_common_mechanism_implemented = True
        self.check_layered_architecture_implemented = False
        # Archan audit parameters
        self.independence_factor = 5
        self.simplicity_factor = 2

    # Rules for mediation matrix generation:
    #
    # Set -1 for items NOT to be considered
    # Set 0 for items which MUST NOT be present
    # Set 1 for items which MUST be present
    #
    # Each module has optional dependencies to itself.
    #
    # - Framework has optional dependency to all framework items (-1),
    #   and to nothing else.
    # - Core libs have dependencies to framework.
    #   Dependencies to other core libs are tolerated.
    # - Application libs have dependencies to framework.
    #   Dependencies to other core or application libs are tolerated.
    #   No dependencies to application modules.
    # - Application modules have dependencies to framework and libs.
    #   Dependencies to other application modules
    #   should be mediated over a broker.
    #   Dependencies to data are tolerated.
    # - Data have no dependencies at all
    #   (but framework/libs would be tolerated).
    @staticmethod
    def _generate_mediation_matrix(dsm):
        """Generate the mediation matrix of the given matrix.

        :type dsm: :class:`DesignStructureMatrix`
        :param dsm: matrix to generate mediation matrix from
        :return: mediation matrix of dsm
        """

        cat = dsm.categories
        ent = dsm.entities
        size = dsm.size
        packages = [e.split('.')[0] for e in ent]

        # define and initialize the mediation matrix
        mediation_matrix = [[0 for x in range(size)]
                            for x in range(size)]

        for i in range(0, size):
            for j in range(0, size):
                if cat[i] == DesignStructureMatrix.framework:
                    if cat[j] == DesignStructureMatrix.framework:
                        mediation_matrix[i][j] = -1
                    else:
                        mediation_matrix[i][j] = 0
                elif cat[i] == DesignStructureMatrix.core_lib:
                    if (cat[j] == DesignStructureMatrix.framework or
                            ent[i].startswith(packages[j] + '.') or
                            i == j):
                        mediation_matrix[i][j] = -1
                    else:
                        mediation_matrix[i][j] = 0
                elif cat[i] == DesignStructureMatrix.app_lib:
                    if (cat[j] == DesignStructureMatrix.framework or
                            cat[j] == DesignStructureMatrix.core_lib or
                            cat[j] == DesignStructureMatrix.app_lib or
                            ent[i].startswith(packages[j] + '.') or
                            i == j):
                        mediation_matrix[i][j] = -1
                    else:
                        mediation_matrix[i][j] = 0
                elif cat[i] == DesignStructureMatrix.app_module:
                    # we cannot force an app module to import things from
                    # the broker if the broker itself did not import anything
                    if (cat[j] == DesignStructureMatrix.framework or
                            cat[j] == DesignStructureMatrix.core_lib or
                            cat[j] == DesignStructureMatrix.app_lib or
                            cat[j] == DesignStructureMatrix.broker or
                            cat[j] == DesignStructureMatrix.data or
                            ent[i].startswith(packages[j] + '.') or
                            i == j):
                        mediation_matrix[i][j] = -1
                    else:
                        mediation_matrix[i][j] = 0
                elif cat[i] == DesignStructureMatrix.broker:
                    # we cannot force the broker to import things from
                    # app modules if there is nothing to be imported
                    if (cat[j] == DesignStructureMatrix.app_module or
                            cat[j] == DesignStructureMatrix.framework or
                            ent[i].startswith(packages[j] + '.') or
                            i == j):
                        mediation_matrix[i][j] = -1
                    else:
                        mediation_matrix[i][j] = 0
                elif cat[i] == DesignStructureMatrix.data:
                    if (cat[j] == DesignStructureMatrix.framework or
                            i == j):
                        mediation_matrix[i][j] = -1
                    else:
                        mediation_matrix[i][j] = 0
                else:
                    mediation_matrix[i][j] = -2  # errors in the generation
                    raise ArchanError(
                        "Mediation matrix value NOT generated for %s:%s" % (
                            i, j))

        return mediation_matrix

    @staticmethod
    def _check_matrices_compliance(dsm, complete_mediation_matrix):
        """Check if matrix and its mediation matrix are compliant.

        :type dsm: :class:`DesignStructureMatrix`
        :param dsm: matrix to check
        :type complete_mediation_matrix: list of list of int
        :param complete_mediation_matrix: 2-dim array (mediation matrix)
        :return: bool, True if compliant, else False
        """

        matrix = dsm.dependency_matrix
        dep_matrix_ok = False
        rows_dep_matrix = len(matrix)
        cols_dep_matrix = len(matrix[0])
        rows_med_matrix = len(complete_mediation_matrix)
        cols_med_matrix = len(complete_mediation_matrix[0])
        if rows_dep_matrix == rows_med_matrix:
            if cols_dep_matrix == cols_med_matrix:
                discrepancy_found = False
                for i in range(0, rows_dep_matrix):
                    for j in range(0, cols_dep_matrix):
                        if ((complete_mediation_matrix[i][j] != -1) and
                                (matrix[i][j] !=
                                    complete_mediation_matrix[i][j])):
                            discrepancy_found = True
                            print("Matrix discrepancy found at "
                                  "%s:%s (%s:%s)" % (
                                i, j, dsm.entities[i], dsm.entities[j]))
                if not discrepancy_found:
                    dep_matrix_ok = True
            else:
                print("Matrices are NOT compliant"
                      "(number of columns not equals)")
        else:
            print("Matrices are NOT compliant (number of rows not equals)")

        return dep_matrix_ok

    def check_complete_mediation(self, dsm):
        """Check if matrix and its mediation matrix are compliant.

        :type dsm: :class:`DesignStructureMatrix`
        :param dsm: matrix to check
        :return: bool, True if compliant, else False
        """

        # generate complete_mediation_matrix according to each category
        med_matrix = Archan._generate_mediation_matrix(dsm)
        matrices_compliant = Archan._check_matrices_compliance(dsm, med_matrix)
        # check comparison result
        return matrices_compliant

    def check_economy_of_mechanism(self, dsm):
        """Check economy of mechanism.

        As first abstraction, number of dependencies between two modules
        < 2 * the number of modules
        (dependencies to the framework are NOT considered).

        :type dsm: :class:`DesignStructureMatrix`
        :param dsm: matrix to check
        :return: bool, True if economic, else False
        """

        # economy_of_mechanism
        economy_of_mechanism = False
        dependency_matrix = dsm.dependency_matrix
        categories = dsm.categories
        dsm_size = dsm.size

        dependency_number = 0
        # evaluate Matrix(dependency_matrix)
        for i in range(0, dsm_size):
            for j in range(0, dsm_size):
                if (categories[i] != DesignStructureMatrix.framework and
                        categories[j] != DesignStructureMatrix.framework and
                        dependency_matrix[i][j] > 0):
                    dependency_number += 1
                    # check comparison result
        if dependency_number < dsm_size * self.simplicity_factor:
            economy_of_mechanism = True
        else:
            print("dependency_number: %s" % dependency_number)
            print("rowsdep_matrix: %s" % dsm_size)
            print("expected dependencies: %s" % self.simplicity_factor)
        return economy_of_mechanism

    def check_separation_of_privileges(self, dsm):
        # separation_of_privileges_matrix
        separation_of_privileges = False
        # check comparison result
        return separation_of_privileges

    def check_least_privileges(self, dsm):
        # least_privileges_matrix
        least_privileges = False
        # check comparison result
        return least_privileges

    def check_least_common_mechanism(self, dsm):
        """Check least common mechanism.

        :type dsm: :class:`DesignStructureMatrix`
        :param dsm: matrix to check
        :return: bool
        """

        # leastCommonMechanismMatrix
        least_common_mechanism = False
        # get the list of dependent modules for each module
        dependency_matrix = dsm.dependency_matrix
        categories = dsm.categories
        dsm_size = dsm.size

        dependent_module_number = []
        # evaluate Matrix(dependency_matrix)
        for j in range(0, dsm_size):
            dependent_module_number.append(0)
            for i in range(0, dsm_size):
                if (categories[i] != DesignStructureMatrix.framework and
                        categories[j] != DesignStructureMatrix.framework and
                        dependency_matrix[i][j] > 0):
                    dependent_module_number[j] += 1
        # except for the broker if any  and libs, check that threshold is not
        # overlapped
        #  index of brokers
        #  and app_libs are set to 0
        for index, item in enumerate(dsm.categories):
            if (item == DesignStructureMatrix.broker or
                    item == DesignStructureMatrix.app_lib):
                dependent_module_number[index] = 0
        if max(
                dependent_module_number
        ) <= old_div(dsm.size, self.independence_factor):
            least_common_mechanism = True
        else:
            print('max number of dependencies to a module: %s' %
                  max(dependent_module_number))
            print('max number of expected dependencies: %s' %
                  int(old_div(dsm.size, self.independence_factor)))

        return least_common_mechanism

    def check_layered_architecture(self):
        # TODO - precondition for subsequent checks?
        # matrices diagonalisée (sauf pour le broker)
        layered_architecture = False
        return layered_architecture

    def check_open_design(self):
        """Check if all criteria checking methods are implemented.

        :return: bool, True if all methods are implemented, else False
        """

        # check that compliance with secure design principles are performed
        open_design = (self.check_complete_mediation_implemented and
                       self.check_economy_of_mechanism_implemented and
                       self.check_separation_of_privileges_implemented and
                       self.check_least_privileges_implemented and
                       self.check_least_common_mechanism_implemented and
                       self.check_layered_architecture_implemented)
        return open_design

    def check_code_clean(self):
        # TODO: flake and mccabe for app_modules
        print("No code issue found.")
        return True

    def check_all(self, dsm):
        return {'CM': self.check_complete_mediation(dsm),
                'EOM': self.check_economy_of_mechanism(dsm),
                'SOP': self.check_separation_of_privileges(dsm),
                'LP': self.check_least_privileges(dsm),
                'LCM': self.check_least_common_mechanism(dsm),
                'LA': self.check_layered_architecture(),
                'OD': self.check_open_design(),
                'CC': self.check_code_clean()}
