from csi.coverage import Dom, RangeDomain


class TestDomain:
    def test_range_int_contents(self):
        d = Dom(RangeDomain(0, 10, 1))
        assert len(d) == 10
        assert 0 in d
        assert 10 not in d
        assert -1 not in d
        assert 5.5 in d

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