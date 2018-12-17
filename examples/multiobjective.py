import sasoptpy as so


def test(cas_conn, sols=True):

    m = so.Model(name='multiobjective', session=cas_conn)

    x = m.add_variables([1, 2], lb=0, ub=5, name='x')

    f1 = m.set_objective((x[1]-1)**2 + (x[1] - x[2]) **2, name='f1', sense=so.MIN, multiobj=True)
    f2 = m.set_objective((x[1]-x[2]) ** 2 + (x[2] - 3)**2, name='f2', sense=so.MIN, multiobj=True)

    m.solve(verbose=True, options={'with': 'lso', 'obj': (f1, f2), 'logfreq': 50})

    print('f1', f1.get_value())
    print('f2', f2.get_value())

    if sols:
        return cas_conn.CASTable('allsols').to_frame()
    else:
        return f1.get_value()
