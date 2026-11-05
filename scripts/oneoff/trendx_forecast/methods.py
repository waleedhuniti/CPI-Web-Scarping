"""Forecast methods on LOG prices. Each returns an array of h log-forecasts."""
import warnings
import numpy as np
warnings.filterwarnings("ignore")
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.arima.model import ARIMA


def naive(y, h):
    return np.repeat(y[-1], h)


def drift(y, h):
    mu = (y[-1] - y[0]) / (len(y) - 1)
    return y[-1] + mu * np.arange(1, h + 1)


def mean_rev_mean(y, h):          # full reversion to the training-window mean
    return np.repeat(y.mean(), h)


def mean_rev_ar1(y, h):           # AR(1) in levels: y_t - m = phi (y_{t-1} - m), phi by OLS, clipped to [0, 1)
    m = y.mean(); a, b = y[:-1] - m, y[1:] - m
    phi = float(np.clip((a @ b) / (a @ a) if (a @ a) > 0 else 1.0, 0.0, 0.999))
    return m + (y[-1] - m) * phi ** np.arange(1, h + 1)


def ses(y, h):
    if np.ptp(y) == 0:
        return naive(y, h)
    f = SimpleExpSmoothing(y, initialization_method="estimated").fit()
    return f.forecast(h)


def holt_damped(y, h):
    if np.ptp(y) == 0:
        return naive(y, h)
    try:
        f = ETSModel(y, error="add", trend="add", damped_trend=True).fit(disp=False)
        return f.forecast(h)
    except Exception:
        return naive(y, h)


def arima_auto(y, h):
    """small AIC grid: ARIMA(0,1,0)+drift, (1,1,0), (0,1,1), AR(1) with mean in levels"""
    if np.ptp(y) == 0:
        return naive(y, h)
    best = None
    for order, trend in [((0, 1, 0), "t"), ((1, 1, 0), "n"), ((0, 1, 1), "n"), ((1, 0, 0), "c")]:
        try:
            r = ARIMA(y, order=order, trend=trend).fit()
            if best is None or r.aic < best[0]:
                best = (r.aic, r)
        except Exception:
            pass
    return naive(y, h) if best is None else best[1].forecast(h)


METHODS = {"naive": naive, "drift": drift, "meanrev_mean": mean_rev_mean, "meanrev_AR1": mean_rev_ar1,
           "ETS_SES": ses, "ETS_damped": holt_damped, "ARIMA_aic": arima_auto}
