"""
Helper functions related to scoring UGC
"""

def map_ores_code_to_int(code):
    """
    Takes a 1-2 letter code from OREs and turns in into an int
    ORES Score map
    Stub - 0
    Start - 1
    C - 2
    B - 3
    GA - 4
    FA - 5
    """
    return {
        'Stub': 0,
        'Start': 1,
        'C': 2,
        'B': 3,
        'GA': 4,
        'FA': 5,
    }[code]
