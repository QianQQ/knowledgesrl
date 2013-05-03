prep = {
    "src":{"from", "out", "out_of", "off", "off_of"},
    "dest_conf": {"into", "onto"},
    "dest_dir": {"for", "at", "to", "towards"},
    "dir":{
        "across", "along", "around", "down", "over", "past", "round",
        "through", "towards", "up"
    },
    "loc":{
        "about", "above", "against", "along", "alongside", "amid", "among",
        "amongst", "around", "astride", "at", "athwart", "before", "behind", "below",
        "beneath", "beside", "between", "beyond", "by", "from", "in", "in_front_of",
        "inside", "near", "next_to", "off", "on", "opposite", "out_of", "outside",
        "over", "round", "throughout", "under", "underneath", "upon", "within"
    }
}

prep["dest"] = prep["dest_conf"] | prep["dest_dir"]
prep["path"] = prep["src"] | prep["dir"] | prep["dest"]
prep["spatial"] = prep["path"] | prep["loc"]

encoutered_preps = {
'among', 'respecting', 'into', 'as', 'through', 'at', 'in', 'before', 'from', 'for', 'to', 'concerning', 'under', 'until', 'over', 'towards', 'out_of', 'between', 'upon', 'regarding', 'in_between', 'with', 'by', 'after', 'on', 'about', 'off', 'of', 'against', 'onto'}

encoutered_lexemes = {
    "as", "apart", "away", "be", "down", "like", "of", "there"
    "to", "together", "up"
}

sub = {
    "how", "that", "where"
}

keywords = set()
for group in prep.values(): keywords = keywords | group
keywords = keywords | encoutered_preps
keywords = keywords | encoutered_lexemes
keywords = keywords | sub


