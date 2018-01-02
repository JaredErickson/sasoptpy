#!/usr/bin/env python
# encoding: utf-8
#
# Copyright SAS Institute
#
#  Licensed under the Apache License, Version 2.0 (the License);
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

'''
Model includes :class:`Model` class, the main structure of an opt. model

'''


from math import inf
from time import time
from types import GeneratorType

import pandas as pd

import sasoptpy.components
import sasoptpy.methods


class Model:
    '''
    Creates an optimization model

    Parameters
    ----------
    name : string
        Name of the model
    session : :class:`swat.cas.connection.CAS` object, optional
        CAS Session object

    Examples
    --------

    >>> from swat import CAS
    >>> import sasoptpy as so
    >>> s = CAS('cas.server.address', port=12345)
    >>> m = so.Model(name='my_model', session=s)
    NOTE: Initialized model my_model

    >>> mip = so.Model(name='mip')
    NOTE: Initialized model mip
    '''

    def __init__(self, name, session=None):
        self._name = sasoptpy.methods.check_name(name, 'model')
        self._session = session
        self._variables = []
        self._constraints = []
        self._objective = sasoptpy.components.Expression()
        self._datarows = []
        self._sense = sasoptpy.methods.MIN
        self._variableDict = {}
        self._constraintDict = {}
        self._vcid = {}
        self._soltime = 0
        self._objval = 0
        self._status = ''
        self._castablename = None
        self._mpsmode = 0
        self._problemSummary = None
        self._solutionSummary = None
        self._primalSolution = pd.DataFrame()
        self._dualSolution = pd.DataFrame()
        self._milp_opts = {}
        self._lp_opts = {}
        sasoptpy.methods.register_name(name, self)
        print('NOTE: Initialized model {}'.format(name))

    def add_variable(self, var=None, vartype=sasoptpy.methods.CONT, name=None,
                     lb=0, ub=inf):
        '''
        Adds a new variable to the model

        New variables can be created via this function or existing variables
        can be added to the model.

        Parameters
        ----------
        var : :class:`Variable` object, optional
            Existing variable to be added to the problem
        vartype : string, optional
            Type of the variable, either 'BIN', 'INT' or 'CONT'
        name : string, optional
            Name of the variable to be created
        lb : float, optional
            Lower bound of the variable
        ub : float, optional
            Upper bound of the variable

        Returns
        -------
        :class:`Variable` object
            Variable that is added to the model

        Examples
        --------
        Adding a variable on the fly

        >>> m = so.Model(name='demo')
        >>> x = m.add_variable(name='x', vartype=so.INT, ub=10)
        >>> print(repr(x))
        NOTE: Initialized model demo
        sasoptpy.Variable(name='x', lb=0, ub=10, vartype='INT')

        Adding an existing variable to a model

        >>> y = so.Variable(name='y', vartype=so.BIN)
        >>> m = so.Model(name='demo')
        >>> m.add_variable(var=y)

        Notes
        -----
        * If argument *var* is not None, then all other arguments are ignored.
        * A generic variable name is generated if name argument is None.

        See also
        --------
        :func:`sasoptpy.Model.include`
        '''
        # name = check_name(name, 'var')
        # Check bounds
        if lb is None:
            lb = 0
        if ub is None:
            ub = inf
        # Existing or new variable
        if var is not None:
            if isinstance(var, sasoptpy.components.Variable):
                self._variables.append(var)
            else:
                print('ERROR: Use the appropriate argument name for variable.')
        else:
            var = sasoptpy.components.Variable(name, vartype, lb, ub)
            self._variables.append(var)
        self._variableDict[var._name] = var
        return var

    def add_variables(self, *argv, vg=None, name=None,
                      vartype=sasoptpy.methods.CONT,
                      lb=None, ub=None):
        '''
        Adds a group of variables to the model

        Parameters
        ----------
        argv : list, dict, :class:`pandas.Index`
            Loop index for variable group
        vg : :class:`VariableGroup` object, optional
            An existing object if it is being added to the model
        name : string, optional
            Name of the variables
        vartype : string, optional
            Type of variables, `BIN`, `INT`, or `CONT`
        lb : list, dict, :class:`pandas.Series`
            Lower bounds of variables
        ub : list, dict, :class:`pandas.Series`
            Upper bounds of variables

        See also
        --------
        :class:`VariableGroup`

        Notes
        -----
        If `vg` argument is passed, all other arguments are ignored.

        Examples
        --------

        >>> production = m.add_variables(PERIODS, vartype=so.INT,
                                        name='production', lb=min_production)
        >>> print(production)
        >>> print(repr(production))
        Variable Group (production) [
          [Period1: production['Period1',]]
          [Period2: production['Period2',]]
          [Period3: production['Period3',]]
        ]
        sasoptpy.VariableGroup(['Period1', 'Period2', 'Period3'],
        name='production')

        '''
        if vg is not None:
            if isinstance(vg, sasoptpy.components.VariableGroup):
                for i in vg:
                    self._variables.append(i)
            else:
                print('ERROR: Cannot add variable group of type {}'.format(
                    type(vg)))
        else:
            name = sasoptpy.methods.check_name(name, 'var')
            vg = sasoptpy.components.VariableGroup(*argv, name=name,
                                                   vartype=vartype,
                                                   lb=lb, ub=ub)
            for i in vg:
                self._variables.append(i)
        for i in vg:
            self._variableDict[i._name] = i
        return vg

    def add_constraint(self, c, name=None):
        '''
        Adds a single constraint to the model

        Parameters
        ----------
        c : Constraint
            Constraint to be added to the model
        name : string, optional
            Name of the constraint

        Returns
        -------
        :class:`Constraint` object

        Examples
        --------

        >>> x = m.add_variable(name='x', vartype=so.INT, lb=0, ub=5)
        >>> y = m.add_variables(3, name='y', vartype=so.CONT, lb=0, ub=10)
        >>> c1 = m.add_constraint(x + y[0] >= 3, name='c1')
        >>> print(c1)
         x  +  y[0]  >=  3

        >>> c2 = m.add_constraint(x - y[2] == [4, 10], name='c2')
        >>> print(c2)
         -  y[2]  +  x  =  [4, 10]

        '''
        if isinstance(c, sasoptpy.components.Constraint):
            # Do not add if the constraint is not valid
            if ((c._direction == 'L' and c._linCoef['CONST']['val'] == -inf) or
               (c._direction == 'G' and c._linCoef['CONST']['val'] == inf)):
                return None
            self._constraints.append(c)
            if name is not None or (name is None and c._name is None):
                name = sasoptpy.methods.check_name(name, 'con')
                c._name = name
                sasoptpy.methods.register_name(name, c)
            self._constraintDict[c._name] = c
            for v in c._linCoef:
                if v != 'CONST':
                    c._linCoef[v]['ref']._tag_constraint(c)
        else:
            raise Exception('Expression is not a constraint!')
        # Return reference to the Constraint object
        return c

    def add_constraints(self, argv, cg=None, name=None):
        '''
        Adds a set of constraints to the model

        Parameters
        ----------
        argv : Generator type objects
            List of constraints as a Generator-type object
        cg : :class:`ConstraintGroup` object, optional
            An existing list of constraints if an existing group is being added
        name : string, optional
            Name for the constraint group and individual constraint prefix

        Returns
        -------
        :class:`ConstraintGroup` object
            A group object for all constraints aded

        Examples
        --------

        >>> x = m.add_variable(name='x', vartype=so.INT, lb=0, ub=5)
        >>> y = m.add_variables(3, name='y', vartype=so.CONT, lb=0, ub=10)
        >>> c = m.add_constraints((x + 2 * y[i] >= 2 for i in [0, 1, 2]),
                                  name='c')
        >>> print(c)
        Constraint Group (c) [
          [0:  2.0 * y[0]  +  x  >=  2]
          [1:  2.0 * y[1]  +  x  >=  2]
          [2:  2.0 * y[2]  +  x  >=  2]
        ]

        >>> t = m.add_variables(3, 4, name='t')
        >>> ct = m.add_constraints((t[i, j] <= x for i in range(3)
                                   for j in range(4)), name='ct')
        >>> print(ct)
        Constraint Group (ct) [
          [(0, 0):  -  x  +  t[0, 0]  <=  0]
          [(0, 1):  t[0, 1]  -  x  <=  0]
          [(0, 2):  -  x  +  t[0, 2]  <=  0]
          [(0, 3):  t[0, 3]  -  x  <=  0]
          [(1, 0):  t[1, 0]  -  x  <=  0]
          [(1, 1):  t[1, 1]  -  x  <=  0]
          [(1, 2):  -  x  +  t[1, 2]  <=  0]
          [(1, 3):  -  x  +  t[1, 3]  <=  0]
          [(2, 0):  -  x  +  t[2, 0]  <=  0]
          [(2, 1):  t[2, 1]  -  x  <=  0]
          [(2, 2):  t[2, 2]  -  x  <=  0]
          [(2, 3):  t[2, 3]  -  x  <=  0]
        ]

        '''
        if cg is not None:
            if isinstance(cg, sasoptpy.components.ConstraintGroup):
                for i in cg:
                    self._constraints.append(i)
                    self._constraintDict[i._name] = i
            else:
                print('ERROR: Cannot add constraint group of type {}'.format(
                    type(cg)))
            return cg
        else:
            if type(argv) == list or type(argv) == GeneratorType:
                name = sasoptpy.methods.check_name(name, 'con')
                cg = sasoptpy.components.ConstraintGroup(argv, name=name)
                for i in cg:
                    self._constraints.append(i)
                    self._constraintDict[i._name] = i
                return cg
            elif type(argv) == sasoptpy.components.Constraint:
                print('WARNING: add_constraints argument is a single' +
                      ' constraint, inserting as a single constraint')
                name = sasoptpy.methods.check_name(name, 'con')
                c = self.add_constraint(c=argv, name=name)
                return c

    def include(self, *argv):
        '''
        Adds existing variables and constraints to a model

        Parameters
        ----------
        argv : :class:`Model`, :class:`Variable`, :class:`Constraint`,
            :class:`VariableGroup`, :class:`ConstraintGroup`
            Objects to be included in the model

        Examples
        --------

        Adding an existing variable

        >>> x = so.Variable(name='x', vartype=so.CONT)
        >>> m.include(x)

        Adding an existing constraint

        >>> c1 = so.Constraint(x + y <= 5, name='c1')
        >>> m.include(c1)

        Adding an existing set of variables

        >>> z = so.VariableGroup(3, 5, name='z', ub=10)
        >>> m.include(z)

        Adding an existing set of constraints

        >>> c2 = so.ConstraintGroup((x + 2 * z[i, j] >= 2 for i in range(3)
                                    for j in range(5)), name='c2')
        >>> m.include(c2)

        Adding an existing model (including its elements)

        >>> new_model = so.Model(name='new_model')
        >>> new_model.include(m)

        Notes
        -----
        * This function is essentially a wrapper for two functions, 
          :func:`sasoptpy.Model.add_variable` and
          :func:`sasoptpy.Model.add_constraint`.
        * Including a model causes all variables and constraints inside the
          original model to be included.
        '''
        for i, c in enumerate(argv):
            if isinstance(c, sasoptpy.components.Variable):
                self.add_variable(var=c)
            elif isinstance(c, sasoptpy.components.VariableGroup):
                for v in c._vardict:
                    self.add_variable(var=c._vardict[v])
            elif isinstance(c, sasoptpy.components.Constraint):
                self.add_constraint(c)
            elif isinstance(c, sasoptpy.components.ConstraintGroup):
                for cn in c._condict:
                    self.add_constraint(c._condict[cn])
            elif isinstance(c, Model):
                for v in c._variables:
                    self.add_variable(v)
                for cn in c._constraints:
                    self.add_constraint(cn)
                self._objective = c._objective
            else:
                print('WARNING: Cannot include argument {} {} {}'.format(
                    i, c, type(c)))

    def set_objective(self, expression, sense, name=None):
        '''
        Sets the objective function for the model

        Parameters
        ----------
        expression : :class:`Expression` object
            The objective function as an Expression
        sense : string
            Objective value direction, 'MIN' or 'MAX'
        name : string, optional
            Name of the objective value

        Returns
        -------
        :class:`Expression`
            Objective function as an :class:`Expression` object

        Examples
        --------

        >>> profit = so.Expression(5 * sales - 2 * material, name='profit')
        >>> m.set_objective(profit, so.MAX)
        >>> print(m.get_objective())
         -  2.0 * material  +  5.0 * sales

        >>> m.set_objective(4 * x - 5 * y, name='obj')
        >>> print(repr(m.get_objective()))
        sasoptpy.Expression(exp =  4.0 * x  -  5.0 * y , name='obj')

        '''
        self._linCoef = {}
        if isinstance(expression, sasoptpy.components.Expression):
            if name is not None:
                obj = expression.copy()
            else:
                obj = expression
        else:
            obj = sasoptpy.components.Expression(expression)
        self._objective = obj
        if self._objective._name is None:
            name = sasoptpy.methods.check_name(name, 'obj')
            sasoptpy.methods.register_name(name, self._objective)
            self._objective._name = name
        self._sense = sense
        return self._objective

    def get_objective(self):
        '''
        Returns the objective function as an :class:`Expression` object

        Returns
        -------
        :class:`Expression` : Objective function

        Examples
        --------

        >>> m.set_objective(4 * x - 5 * y, name='obj')
        >>> print(repr(m.get_objective()))
        sasoptpy.Expression(exp =  4.0 * x  -  5.0 * y , name='obj')

        '''
        return self._objective

    def get_objective_value(self):
        '''
        Returns the optimal objective value, if it exists

        Returns
        -------
        float : Objective value at current solution

        Examples
        --------

        >>> m.solve()
        >>> print(m.get_objective_value())
        42.0

        '''
        return self._objective.get_value()

    def get_variable(self, name):
        '''
        Returns the reference to a variable in the model

        Parameters
        ----------
        name : string
            Name or key of the variable requested

        Returns
        -------
        :class:`Variable` object

        Examples
        --------

        >>> m.add_variable(name='x', vartype=so.INT, lb=3, ub=5)
        >>> var1 = m.get_variable('x')
        >>> print(repr(var1))
        sasoptpy.Variable(name='x', lb=3, ub=5, vartype='INT')

        '''
        for v in self._variables:
            if v._name == name:
                return v

    def get_variable_coef(self, var):
        '''
        Returns the objective value coefficient of a variable

        Parameters
        ----------
        var : :class:`Variable` object or string
            Variable whose objective value is requested or its name

        Returns
        -------
        float
            Objective value coefficient of the given variable

        Examples
        --------

        >>> x = m.add_variable(name='x')
        >>> y = m.add_variable(name='y')
        >>> m.set_objective(4 * x - 5 * y, name='obj', sense=so.MAX)
        >>> print(m.get_variable_coef(x))
        4.0
        >>> print(m.get_variable_coef('y'))
        -5.0

        '''
        if isinstance(var, sasoptpy.components.Variable):
            varname = var._name
        else:
            varname = var
        if varname in self._objective._linCoef:
            return self._objective._linCoef[varname]['val']
        else:
            return 0

    def get_problem_summary(self):
        '''
        Returns the problem summary table to the user

        Returns
        -------
        :class:`swat.dataframe.SASDataFrame` object
            Problem summary obtained after :func:`sasoptpy.Model.solve`

        Examples
        --------

        >>> m.solve()
        >>> ps = m.get_problem_summary()
        >>> print(type(ps))
        <class 'swat.dataframe.SASDataFrame'>

        >>> print(ps)
        Problem Summary
                                        Value
        Label
        Problem Name                   model1
        Objective Sense          Maximization
        Objective Function                obj
        RHS                               RHS
        Number of Variables                 2
        Bounded Above                       0
        Bounded Below                       2
        Bounded Above and Below             0
        Free                                0
        Fixed                               0
        Number of Constraints               2
        LE (<=)                             1
        EQ (=)                              0
        GE (>=)                             1
        Range                               0
        Constraint Coefficients             4

        >>> print(ps.index)
        Index(['Problem Name', 'Objective Sense', 'Objective Function', 'RHS',
        '', 'Number of Variables', 'Bounded Above', 'Bounded Below',
        'Bounded Above and Below', 'Free', 'Fixed', '',
        'Number of Constraints', 'LE (<=)', 'EQ (=)', 'GE (>=)', 'Range', '',
        'Constraint Coefficients'],
        dtype='object', name='Label')

        >>> print(ps.loc['Number of Variables'])
        Value               2
        Name: Number of Variables, dtype: object

        >>> print(ps.loc['Constraint Coefficients', 'Value'])
        4

        '''
        return self._problemSummary

    def get_solution_summary(self):
        '''
        Returns the solution summary table to the user

        Returns
        -------
        :class:`swat.dataframe.SASDataFrame` object
            Solution summary obtained after solve

        Examples
        --------

        >>> m.solve()
        >>> soln = m.get_solution_summary()
        >>> print(type(soln))
        <class 'swat.dataframe.SASDataFrame'>

        >>> print(soln)
        Solution Summary
                                       Value
        Label
        Solver                            LP
        Algorithm               Dual Simplex
        Objective Function               obj
        Solution Status              Optimal
        Objective Value                   10
        Primal Infeasibility               0
        Dual Infeasibility                 0
        Bound Infeasibility                0
        Iterations                         2
        Presolve Time                   0.00
        Solution Time                   0.01

        >>> print(soln.index)
        Index(['Solver', 'Algorithm', 'Objective Function', 'Solution Status',
               'Objective Value', '', 'Primal Infeasibility',
               'Dual Infeasibility', 'Bound Infeasibility', '', 'Iterations',
               'Presolve Time', 'Solution Time'],
              dtype='object', name='Label')

        >>> print(soln.loc['Solution Status', 'Value'])
        Optimal

        '''
        return self._solutionSummary

    def get_solution(self, vtype='Primal'):
        '''
        Returns the solution details associated with the primal or dual
        solution

        Parameters
        ----------
        vtype : string, optional
            'Primal' or 'Dual'

        Returns
        -------
        :class:`pandas.DataFrame` object
            Primal or dual solution table returned from the CAS Action

        Examples
        --------

        >>> m.solve()
        >>> print(m.get_solution('Primal'))
              _OBJ_ID_ _RHS_ID_               _VAR_ _TYPE_  _OBJCOEF_  _LBOUND_
        0  totalProfit      RHS      production_cap      I      -10.0       0.0
        1  totalProfit      RHS  production_Period1      I       10.0       5.0
        2  totalProfit      RHS  production_Period2      I       10.0       5.0
        3  totalProfit      RHS  production_Period3      I       10.0       0.0
             _UBOUND_  _VALUE_
        1.797693e+308     25.0
        1.797693e+308     25.0
        1.797693e+308     15.0
        1.797693e+308     25.0

        >>> print(m.get_solution('Dual'))
              _OBJ_ID_ _RHS_ID_       _ROW_ _TYPE_  _RHS_  _L_RHS_  _U_RHS_
        0  totalProfit      RHS  capacity_0      L    0.0      NaN      NaN
        1  totalProfit      RHS  capacity_1      L    0.0      NaN      NaN
        2  totalProfit      RHS  capacity_2      L    0.0      NaN      NaN
        3  totalProfit      RHS    demand_0      L   30.0      NaN      NaN
        4  totalProfit      RHS    demand_1      L   15.0      NaN      NaN
        5  totalProfit      RHS    demand_2      L   25.0      NaN      NaN
        _ACTIVITY_
               0.0
             -10.0
               0.0
              25.0
              15.0
              25.0

        '''
        if vtype == 'Primal':
            return self._primalSolution
        elif vtype == 'Dual':
            return self._dualSolution
        else:
            return None

    def set_session(self, session):
        '''
        Sets the CAS session for model

        Parameters
        ----------
        session : :class:`swat.cas.connection.CAS`
            CAS Session
        '''
        from swat import CAS
        if type(session) == CAS:
            self._session = session
        else:
            print('WARNING: Session is not added, not a CAS object.')

    def set_coef(self, var, con, value):
        '''
        Updates the coefficient of a variable inside constraints

        Parameters
        ----------
        var : :class:`Variable` object
            Variable whose coefficient will be updated
        con : :class:`Constraint` object
            Constraint where the coefficient will be updated
        value : float
            The new value for the coefficient of the variable

        Examples
        --------

        >>> c1 = m.add_constraint(x + y >= 1, name='c1')
        >>> print(c1)
        y  +  x  >=  1
        >>> m.set_coef(x, c1, 3)
        >>> print(c1)
        y  +  3.0 * x  >=  1

        Notes
        -----
        Variable coefficient inside the constraint is replaced in-place.

        See also
        --------
        :func:`sasoptpy.Constraint.update_var_coef`

        '''
        con.update_var_coef(var=var, value=value)

    def print_solution(self):
        '''
        Prints the current values of the variables

        Examples
        --------

        >>> m.solve()
        >>> m.print_solution()
        x: 2.0
        y: 0.0

        See also
        --------
        :func:`sasoptpy.Model.get_solution`

        '''
        for v in self._variables:
            print('{}: {}'.format(v._name, v._value))

    def _append_row(self, row):
        '''
        Appends a new row to the model representation

        Parameters
        ----------
        row : list
            A new row to be added to the model representation for MPS format

        Returns
        -------
        int
            Current number for the ID column
        '''
        self._datarows.append(row + [str(self._id)])
        rowid = self._id
        self._id = self._id+1
        return rowid

    def to_frame(self):
        '''
        Converts the Python model into a DataFrame object in MPS format

        Returns
        -------
        :class:`pandas.DataFrame` object
            Problem in strict MPS format

        Examples
        --------

        >>> df = m.to_frame()
        >>> print(df)
             Field1 Field2  Field3 Field4 Field5 Field6 _id_
        0      NAME         model1      0             0    1
        1      ROWS                                        2
        2       MAX    obj                                 3
        3         L     c1                                 4
        4   COLUMNS                                        5
        5                x     obj      4                  6
        6                x      c1      3                  7
        7                y     obj     -5                  8
        8                y      c1      1                  9
        9       RHS                                       10
        10             RHS      c1      6                 11
        11   RANGES                                       12
        12   BOUNDS                                       13
        13   ENDATA                     0             0   14

        Notes
        -----
        * This function is called inside :func:`sasoptpy.Model.solve`.
        '''
        print('NOTE: Converting model {} to data frame'.format(self._name))
        self._id = 1
        if(len(self._datarows) > 0):  # For future reference
            # take a copy?
            self._mpsmode = 1
            self._datarows = []
        else:
            self._datarows = []
        # Check if objective has a constant field, if so hack using a variable
        if self._objective._linCoef['CONST']['val'] != 0:
            obj_constant = self.add_variable(name=sasoptpy.methods.check_name(
                'obj_constant', 'var'))
            constant_value = self._objective._linCoef['CONST']['val']
            obj_constant.set_bounds(lb=constant_value, ub=constant_value)
            obj_constant._value = constant_value
            obj_name = self._objective._name + '_constant'
            self._objective = self._objective - constant_value + obj_constant
            self._objective._name = obj_name
            print('WARNING: The objective function contains a constant term.' +
                  ' An auxiliary variable is added.')
        # self._append_row(['*','SAS-Viya-Opt','MPS-Free Format','0','0','0'])
        self._append_row(['NAME', '', self._name, 0, '', 0])
        self._append_row(['ROWS', '', '', '', '', ''])
        if self._objective._name is not None:
            self._append_row([self._sense, self._objective._name,
                             '', '', '', ''])

        for c in self._constraints:
            self._append_row([c._direction, c._name, '', '', '', ''])
        self._append_row(['COLUMNS', '', '', '', '', ''])
        curtype = sasoptpy.methods.CONT
        for v in self._variables:
            f5 = 0
            self._vcid[v._name] = {}
            if v._type is sasoptpy.methods.INT and\
                    curtype is sasoptpy.methods.CONT:
                self._append_row(['', 'MARK0000', '\'MARKER\'', '',
                                 '\'INTORG\'', ''])
                curtype = sasoptpy.methods.INT
            if v._type is not sasoptpy.methods.INT\
                    and curtype is sasoptpy.methods.INT:
                self._append_row(['', 'MARK0001', '\'MARKER\'', '',
                                 '\'INTEND\'', ''])
                curtype = sasoptpy.methods.CONT
            if v._name in self._objective._linCoef:
                cv = self._objective._linCoef[v._name]
                current_row = ['', v._name, self._objective._name, cv['val']]
                f5 = 1
            for cn in v._cons:
                if cn in self._constraintDict:
                    c = self._constraintDict[cn]
                    if v._name in c._linCoef:
                        if f5 == 0:
                            current_row = ['', v._name, c._name,
                                           c._linCoef[v._name]['val']]
                            f5 = 1
                        else:
                            current_row.append(c._name)
                            current_row.append(c._linCoef[v._name]['val'])
                            ID = self._append_row(current_row)
                            self._vcid[v._name][current_row[2]] = ID
                            self._vcid[v._name][current_row[4]] = ID
                            f5 = 0
            if f5 == 1:
                current_row.append('')
                current_row.append('')
                ID = self._append_row(current_row)
                self._vcid[v._name][current_row[2]] = ID
        if curtype is sasoptpy.methods.INT:
            self._append_row(['', 'MARK0001', '\'MARKER\'', '', '\'INTEND\'',
                             ''])
        self._append_row(['RHS', '', '', '', '', ''])
        f5 = 0
        for c in self._constraints:
            if c._direction == 'L' and c._linCoef['CONST']['val'] == -inf:
                continue
            if c._direction == 'G' and c._linCoef['CONST']['val'] == 0:
                continue
            rhs = - c._linCoef['CONST']['val']
            if rhs != 0:
                if f5 == 0:
                    current_row = ['', 'RHS', c._name, rhs]
                    f5 = 1
                else:
                    current_row.append(c._name)
                    current_row.append(rhs)
                    #self._append_row(['', 'RHS', c._name, rhs, '', ''])
                    f5 = 0
                    self._append_row(current_row)
        if f5 == 1:
            current_row.append('')
            current_row.append('')
            self._append_row(current_row)
        self._append_row(['RANGES', '', '', '', '', ''])
        for c in self._constraints:
            if c._range != 0:
                self._append_row(['', 'rng', c._name, c._range, '', ''])
        self._append_row(['BOUNDS', '', '', '', '', ''])
        for v in self._variables:
            if self._vcid[v._name] == {}:
                continue
            if v._lb is not 0 and v._lb is not None:
                if v._ub == inf and v._lb == -inf:
                    self._append_row(['FR', 'BND', v._name, '', '', ''])
                else:
                    self._append_row(['LO', 'BND', v._name, v._lb, '', ''])
            if v._ub != inf and v._ub is not None and not\
               (v._type is sasoptpy.methods.BIN and v._ub == 1):
                self._append_row(['UP', 'BND', v._name, v._ub, '', ''])
            if v._type is sasoptpy.methods.BIN:
                self._append_row(['BV', 'BND', v._name, '1.0', '', ''])
            if v._lb is 0 and v._type is sasoptpy.methods.INT:
                self._append_row(['LO', 'BND', v._name, v._lb, '', ''])
        self._append_row(['ENDATA', '', '', float(0), '', float(0)])
        mpsdata = pd.DataFrame(data=self._datarows,
                               columns=['Field1', 'Field2', 'Field3', 'Field4',
                                        'Field5', 'Field6', '_id_'])
        return mpsdata

    def __str__(self):
        s = 'Model: [\n'
        s += '  Name: {}\n'.format(self._name)
        if self._session is not None:
            s += '  Session: {}:{}\n'.format(self._session._hostname,
                                             self._session._port)
        s += '  Objective: {} [{}]\n'.format(self._sense,
                                             self._objective)
        s += '  Variables ({}): [\n'.format(len(self._variables))
        for i in self._variables:
            s += '    {}\n'.format(i)
        s += '  ]\n'
        s += '  Constraints ({}): [\n'.format(len(self._constraints))
        for i in self._constraints:
            s += '    {}\n'.format(i)
        s += '  ]\n'
        s += ']'
        return s

    def __repr__(self):
        s = 'sasoptpy.Model(name=\'{}\', session={})'.format(self._name,
                                                             self._session)
        return s

    def upload_user_blocks(self):
        '''
        Uploads user-defined decomposition blocks to the CAS server

        Returns
        -------
        string
            CAS table name of the user-defined decomposition blocks

        Examples
        --------

        >>> userblocks = m.upload_user_blocks()
        >>> m.solve(milp={'decomp': {'blocks': userblocks}})

        '''
        sess = self._session
        if sess is None:
            print('ERROR: CAS Session is not defined for model {}.'.format(
                self._name))
            return None
        decomp_table = []
        for c in self._constraints:
            if c._block is not None:
                decomp_table.append([c.get_name(), c._block])
        frame_decomp_table = pd.DataFrame(decomp_table,
                                          columns=['_ROW_', '_BLOCK_'])
        response = sess.upload_frame(frame_decomp_table, casout='BLOCKSTABLE')
        return(response.name)

    def solve(self, milp={}, lp={}):
        '''
        Solves the model by calling CAS optimization solvers

        Parameters
        ----------
        milp : dict
            A dictionary of MILP options for the solveMilp CAS Action
        lp : dict
            A dictionary of LP options for the solveLp CAS Action

        Returns
        -------
        :class:`pandas.DataFrame` object
            Solution of the optimization model

        Examples
        --------

        >>> m.solve()
        NOTE: Initialized model food_manufacture_1
        NOTE: Converting model food_manufacture_1 to data frame
        NOTE: Added action set 'optimization'.
        ...
        NOTE: Optimal.
        NOTE: Objective = 107842.59259.
        NOTE: The Dual Simplex solve time is 0.01 seconds.
        NOTE: Data length = 419 rows
        NOTE: Conversion to MPS =   0.0010 secs
        NOTE: Upload to CAS time =  0.1420 secs
        NOTE: Solution parse time = 0.2500 secs
        NOTE: Server solve time =   0.1168 secs

        >>> m.solve(milp={'maxtime': 600})

        >>> m.solve(lp={'algorithm': 'ipm'})

        Notes
        -----
        * This function takes two optional arguments (milp and lp).
        * These arguments pass options to the solveLp and solveMilp CAS
          actions.
        * Both milp and lp should be defined as dictionaries, where keys are
          option names. For example, ``m.solve(milp={'maxtime': 600})`` limits
          solution time to 600 seconds.
        * See http://go.documentation.sas.com/?cdcId=vdmmlcdc&cdcVersion=8.11&docsetId=casactmopt&docsetTarget=casactmopt_solvelp_syntax.htm&locale=en for a list of LP options.
        * See http://go.documentation.sas.com/?cdcId=vdmmlcdc&cdcVersion=8.11&docsetId=casactmopt&docsetTarget=casactmopt_solvemilp_syntax.htm&locale=en for a list of MILP options.

        '''

        # Check if session is defined
        sess = self._session
        if sess is None:
            print('ERROR: CAS Session is not defined for model {}.'.format(
                self._name))
            return None

        # Pre-upload argument parse
        opt_args = lp
        if bool(lp):
            self._lp_opts = lp
        if bool(milp):
            self._milp_opts = milp
            opt_args = milp

        # Decomp check
        user_blocks = None
        if 'decomp' in opt_args:
            if 'method' in opt_args['decomp']:
                if opt_args['decomp']['method'] == 'user':
                    user_blocks = self.upload_user_blocks()
                    opt_args['decomp'] = {'blocks': user_blocks}

        # Conversion and upload
        time0 = time()
        df = self.to_frame()
        time1 = time()
        sess.loadactionset(actionset='optimization')
        time2 = time()
        print('NOTE: Uploading the problem data frame to the server.')
        m = sess.upload_frame(data=df)
        time3 = time()

        # Solve based on problem type
        ptype = 1  # LP
        for v in self._variables:
            if v._type != sasoptpy.methods.CONT:
                ptype = 2
        if ptype == 1:
            response = sess.solveLp(data=m.name,
                                    **self._lp_opts,
                                    primalOut={'caslib': 'CASUSER',
                                               'name': 'primal',
                                               'replace': True},
                                    dualOut={'caslib': 'CASUSER',
                                             'name': 'dual', 'replace': True},
                                    objSense=self._sense)
        elif ptype == 2:
            response = sess.solveMilp(data=m.name,
                                      **self._milp_opts,
                                      primalOut={'caslib': 'CASUSER',
                                                 'name': 'primal',
                                                 'replace': True},
                                      dualOut={'caslib': 'CASUSER',
                                               'name': 'dual',
                                               'replace': True},
                                      objSense=self._sense)
        time4 = time()

        # Parse solution
        if(response.get_tables('status')[0] == 'OK'):
            self._primalSolution = sess.CASTable('primal',
                                                 caslib='CASUSER').to_frame()
            self._dualSolution = sess.CASTable('dual',
                                               caslib='CASUSER').to_frame()
            # Bring solution to variables
            for _, row in self._primalSolution.iterrows():
                self._variableDict[row['_VAR_']]._value = row['_VALUE_']
        time5 = time()

        # Print timings
        print('NOTE: Data length = {} rows'.format(len(df)))
        print('NOTE: Conversion to MPS =   {:.4f} secs'.format(time1-time0))
        print('NOTE: Upload to CAS time =  {:.4f} secs'.format(time3-time2))
        print('NOTE: Solution parse time = {:.4f} secs'.format(time5-time4))
        print('NOTE: Server solve time =   {:.4f} secs'.format(time4-time3))

        # Drop tables
        sess.table.droptable(table=m.name)
        if user_blocks is not None:
            sess.table.droptable(table=user_blocks)

        # Post-solve parse
        if(response.get_tables('status')[0] == 'OK'):
            # Print problem and solution summaries
            self._problemSummary = response.ProblemSummary[['Label1',
                                                            'cValue1']]
            self._solutionSummary = response.SolutionSummary[['Label1',
                                                              'cValue1']]
            self._problemSummary.set_index(['Label1'], inplace=True)
            self._problemSummary.columns = ['Value']
            self._problemSummary.index.names = ['Label']
            self._solutionSummary.set_index(['Label1'], inplace=True)
            self._solutionSummary.columns = ['Value']
            self._solutionSummary.index.names = ['Label']
            print(self._problemSummary)
            print(self._solutionSummary)
            # Record status and time
            self._status = response.solutionStatus
            self._soltime = response.solutionTime
            if('OPTIMAL' in response.solutionStatus):
                self._objval = response.objective
                return self._primalSolution
            else:
                print('NOTE: Response {}'.format(response.solutionStatus))
                self._objval = 0
                return None
        else:
            print('ERROR: {}'.format(response.get_tables('status')[0]))
            return None