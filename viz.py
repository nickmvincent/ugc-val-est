import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
sns.set_style("whitegrid")
sns.set_context("talk", font_scale=2)
sns.set_color_codes('muted')

name = 'vizdata'

data = pd.read_csv(name + '.csv', names=['platform', 'score', 'cond'])


palette = {'WP': 'b', 'No WP': 'r', 'WP upper-bound': 'b', 'WP lower-bound': 'g'}
ax = sns.factorplot(
    x="cond", y="score", row='platform', 
    data=data,
    sharey=False,
    size=5,
    aspect=3,
    kind='bar',
    palette=palette,
)
ax.set_xlabels("")
ax.set_titles("")
plt.savefig(name + '.png', bbox_inches='tight', dpi=300)
plt.show()
