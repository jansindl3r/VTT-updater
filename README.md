# VTT-updater

## Copies VTT instructions from old file into new one...

### What is VTT?
VTT is a tool for creating complex and powerful TrueType hinting in the best possible way. TrueType hinting is becoming least relevant every year, the community is becoming smaller and smaller and xxxx. There has been a discussion whether it should be open sourced and it looks that it might get one day! VTT has runs on Windows recently we got commandline interface for it and some voices on typedrawers.

### How does VTT store its files?
VTT saves its files in TTF. From outside you can't tell them apart, except VTT files tend to be much larger. Inside they contain additional tables __TSI0, TSI1, TSI2, TSI3, TSI4 & TSI5__. TSI3 f.e. holds probably the most important data of your VTT workflow – instructions for each individual glyph.

### So how does this tool updates VTT files?
- It compares VTT file with TTF file in which you want import the instructions. 
- It warns you that there are incompatible glyphs and it won't import these.
- If glyph names differ, f.e. one font uses production names and the others doesnt, then it remaps glyphs based on their unicodes. Glyphs without unicode won't be remapped.
- It copies values from _maxp_ and _head_ table. 

### What is this __legacy__ thing in this tool?
VTT-updater has lived for some years, I learnt how to code a bit better and how to deliver better solution for this problem. The older solution took advange of the possibility of exporting a XML file with all the data. This extra step made things much complicated to inconporate into one's workflow.

### How do I start?
1. Having Python installed is the first step, make sure you have it. There are plenty of tutorials already out there. This tool won't run without it. Make sure it works on your machine, you can test it by opening your terminal, typing `python` or `python 3` and hitting `enter`. 
1. You need to have `fontTools` installed. If you don't have it yet, run command `[python/python3] -m pip install fonttools`
1. Run `vtt_updater` by navigating to where you copied this repository and run `[python/python3] Lib/vtt_updater.py vtt.ttf exported.ttf`

### Ok, I got it. How do I control it, so it works with my fonts?
there are two positional arguments
1. Path to a font containing VTT instructions  
1. Path to a font in which you want to import the instructions
there are few optional arguments
1. `-s, --save_to` path where to save the updated file.   
1. `--log` prints out warnings about incompatible contours
1. `--legacy` uses legacy code that has been available until January 2021. Legacy version requires additional `XML` file which you can obtain in VTT under `File > Export > All code to XML`. 

### Happy VTT!

```
###########################
### |####/ __  _____  __/##
### |##/ /##/ /####/ /#####
###  / /###/ /####/ /######
###__/####/_/####/_/#######
###########################
``` 