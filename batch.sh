python db_helpers.py save_links_and_posts
python db_helpers.py print_potential_wikilinks


python prediction.py --rq 1
python prediction.py --rq 2

python prediction.py --platform s --rq 1-is_top
python prediction.py --platform s --rq 2-is_top

python stats.py --rq 10
python stats.py --rq 10 --frequency --sample_num 0,1,2
python stats.py --rq 2
python stats.py --rq 3
python stats.py --platform s --rq 13
python stats.py --platform s --rq 14
python stats.py --platform s --rq 33
