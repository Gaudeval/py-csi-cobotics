from csi.coverage import Dom, RangeDomain, SpaceDomain


class TestDomain:
    def test_range_int_contents(self):
        d = Dom(RangeDomain(0, 10, 1))
        assert len(d) == 10
        assert 0 in d
        assert 10 not in d
        assert -1 not in d
        assert 5.5 in d

        d = Dom(RangeDomain(0, 100, 75))
        assert 80 in d
        assert 0 in d
        assert 99 in d

    def test_range_float_contents(self):
        d = Dom(RangeDomain(0, 10, 0.5))
        assert 0 in d
        assert 10 not in d
        assert -1 not in d
        assert 5.5 in d

    def test_empty_range(self):
        d = Dom(RangeDomain(0, 0, 1))
        assert len(d) == 0
        d = Dom(RangeDomain(2, 2, 1))
        assert len(d) == 0
        d = Dom(RangeDomain(1, -1, 1))
        assert len(d) == 0
        d = Dom(RangeDomain(1, -1, -1))
        assert len(d) == 0

    def test_range_int_values(self):
        d = Dom(RangeDomain(0, 10, 1))
        assert d.value(5) == 5
        assert d.value(11) is None
        assert d.value(5.5) == 5

        d = Dom(RangeDomain(0, 100, 75))
        assert d.value(80) == 75
        assert d.value(25) == 0

    def test_space_contents(self):
        d = Dom(SpaceDomain(0, 10, 2))
        assert 0 in d
        assert 10 not in d
        assert 9 in d
        assert 0.1 in d
        assert 0.5 in d
        assert 5 in d

        d = Dom(SpaceDomain(0, 10, 4))
        assert 0 in d
        assert 10 not in d
        assert 9 in d
        assert 0.1 in d
        assert 0.5 in d
        assert 5 in d

        d = Dom(SpaceDomain(0, 1, 1))
        assert 0 in d
        assert 10 not in d
        assert 0.1 in d
        assert 0.5 in d
        assert 1 not in d

    def test_space_values(self):
        d = Dom(SpaceDomain(0, 10, 4))
        assert d.value(0) == 0
        assert d.value(2.4) == 0
        assert d.value(2.5) == 2.5
        assert d.value(3) == 2.5
        assert d.value(5) == 5
        assert d.value(6) == 5
        assert d.value(7.5) == 7.5
        assert d.value(9) == 7.5

        d = Dom(SpaceDomain(0, 1, 1))
        assert d.value(0) == 0
        assert d.value(0.1) == 0
        assert d.value(0.15) == 0
        assert d.value(0.99) == 0
        assert d.value(0.66) == 0

        # TODO Test with non 0 base
        # TODO Test with negative - positive interval
        # TODO Test with pure negative interval
