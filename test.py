

# re-run causal analysis with test data to make sure you didn't break it :)
import numpy as np
from causalinference import CausalModel

from causalinference.utils.tools import vignette_data

Y, D, X = vignette_data()

Y = np.array([Y, Y]).T
ids = np.array(range(len(Y)))

causal = CausalModel(Y, D, X, ids=ids)

print(causal.summary_stats)
causal.est_via_ols()
print(causal.estimates)
causal.est_propensity_s()
print(causal.propensity)
causal.trim_s()
causal.stratify_s()
print(causal.strata)
causal.est_via_blocking([], [])
print(causal.estimates)
print(causal.estimates.keys())

## expected ATT is 9.553