"""Interface and definitions for foreign exchange rate readers.
"""
import six

from interface import implements

from .base import FXRateReader


class InMemoryFXRateReader(implements(FXRateReader)):
    """
    A simple in-memory FXRateReader.

    This is primarily used for testing.

    Parameters
    ----------
    data : dict
        Nested map from rate name -> quote currency -> pd.DataFrame
        Leaf frames should be indexed by (dates, base currencies).
    default_rate : str
        Rate to use when ``get_rates`` is called with a rate of 'default'.
    """

    def __init__(self, data, default_rate):
        self._data = data
        self._default_rate = default_rate

    def get_rates(self, rate, quote, bases, dts):
        """Get rates to convert ``bases`` into ``quote``.
        """
        if rate == 'default':
            rate = self._default_rate

        if six.PY3:
            # DataFrames in self._data contain str as column keys, which don't
            # compare equal to numpy bytes objects in Python 3. Convert to
            # unicode to make comparisons work as expected.
            cols = bases.astype('U3')
        else:
            # In py2, just use bases unchanged.
            cols = bases

        df = self._data[rate][quote]

        self._check_dts(df.index, dts)

        # Get raw values out of the frame.
        #
        # Logically, the operation here is:
        #
        # (df
        #  .reindex(dts, side='right')
        #  .reindex_axis(cols, axis='columns')
        #  .values)
        #
        # But pandas' performance on the above is not great, and we call this
        # method a lot, so we implement our own indexing logic.

        values = df.values
        row_ixs = df.index.searchsorted(dts, side='right') - 1
        col_ixs = df.columns.get_indexer(cols)

        return values[row_ixs][:, col_ixs]

    def _check_dts(self, stored, requested):
        """Validate that requested dates are in bounds for what we have stored.
        """
        request_start, request_end = requested[[0, -1]]
        data_start, data_end = stored[[0, -1]]

        if request_start < data_start:
            raise ValueError(
                "Requested fx rates starting at {}, but data starts at {}"
                .format(request_start, data_start)
            )

        if request_end > data_end:
            raise ValueError(
                "Requested fx rates ending at {}, but data ends at {}"
                .format(request_end, data_end)
            )
