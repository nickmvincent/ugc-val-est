
from causalinference import CausalModel

from causalinference.utils.tools import vignette_data

Y, D, X = vignette_data()

causal = CausalModel(Y, D, X)

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
print(causal.estimates.key())