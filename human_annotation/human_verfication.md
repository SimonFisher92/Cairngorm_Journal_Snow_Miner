# Human Annotation and Verification

Thank you for your interest in contributing to the project. Human verification is sadly (or not) needed, to ensure the quality and accuracy of the snow patch data. Below are the guidelines and steps to follow for human annotation and verification.

## Overview

I hope you find this tool maximally efficient, GPT will have attempted to get all of this correct (so the entries will be pre-populated), but that isnt always true, particularly with dates. Here are the functions of the main entries/buttons:

`Date` : Input/correct the date as per the guidelines below (use same as previous if appropriate)

`Location` : Input/correct the location as per the guidelines below (use same as previous if appropriate)

`Annotator Comment` : Any comments you have about the entry- particularly if you have had to make a judgement call. Dont use this often as it will slow you down.

`Save` : Saves the entry

`Skip` : Skips the entry, basically the GPT entry was perfect so proceed without changes

`Reject Suggestion` : Rejects the entry, some examples of this could be inappropriate locations ie walking in the alps, or mentions of animals like snow buntings. I find I use this 20-30% of the time.

`Quit` : Quits the program without finishing. NB the program with automatically save after the last snippet is processed.

The tool will automatically jump and highlight text, but you can jump back using the `Jump to highlight` or the `Enhanced Jump` button. The enhanced jump is more memory intensive but will work even if GPT has hallucinated a bit (see below).

## Guidelines for Human Annotation and Verification

### Section 1: Date parsing

I have thought about this pretty hard. The date parsing is a bit tricky, because the dates are often spans and not days.
Here are the rules I would like to suggest:

1. If the date is a *single day*, use that date. Format the date like `DD/MM/YYYY`.  
2. If the date is a *range within a week* (e.g., "from Monday to Friday"), use the first date of the range. Format the date like `DD/MM/YYYY`. Dont bother backcalculating dates unless its extremely important (ie the day a snowpatch melted)- if it feels like the second week in April, then just go `07/04/YYYY`- this tool is about efficiency and a day here or there over this timeline is not significant.

3. If the date is a range that spans multiple weeks or a month, then do not provide a day, simply input a '-' for the day. Format the date like `-/MM/YYYY`.
4. If the date is a range that spans a season then just put the season and the year, aka `Winter YYYY`, `Spring YYYY`, `Summer YYYY`, `Autumn YYYY`.
5. If its utterly unclear, then just put `YYYY` which can be obtained from the front page of the journal.

### Section 2: Location Parsing

Most of the time, GPTs location extractions are pretty good, but you may wish to update them.

1. If the location is a *specific named place* (e.g., "Ben Macdui"), use that name as is. It gets a little tricky because many of the munro names use older Gaidhlig spelling in older journals. Either Anglicise them or dont- your call. I think some harmonisation will be needed down the line.
2. If the location is a *general area* (e.g., "Cairngorms"), use that name as is.
3. If the location is a *range of places* (e.g., "from Ben Nevis to Glencoe"), then just go with that.

### Section 3: Dealing with Snippet Hallcuinations

If GPT has hallucinated then the normal "red", `jump to highlight` will not function as its a string matching process. In those cases use the `enhanced jump` button- this does a more memory intensive matching. There are a couple of benign reasons why you might need to use the enhanced jump- but sometime it will be because of a hallcuination. In those cases, use the text entry to update the snippet with the real string

## Using the Tool

I prefer to use conda for enviroment management. You can create a new conda environment with the required dependencies by running:

```bash
cd path/to/your/project # (particularly where requirements.txt is)
conda create --name snowpatch_annotation python=3.10
conda activate snowpatch_annotation
pip install -r requirements.txt
```

Then you can run the annotation tool from your command line (remember you need to be in your enviroment). It uses arsgparse to take command line arguments. Here is an example command:

```bash
cd path/to/your/project/human_annotation
python enhanced_human_verification.py --issue 002 --uncleaned_dir C:\Projects\Cairngorm_Journal_Snow_miner\human_annotation\uncleaned --pdf_dir C:\Projects\Cairngorm_Journal_Snow_miner\human_annotation\pdf --out C:\Projects\Cairngorm_Journal_Snow_miner\human_annotation\hand_curated
```

the arguments are:

`--issue` : The issue number you are working on (e.g., 002 for issue 2). The corresponding pdf and uncleaned files should exist in their directories. NB these are issue number and not year because some years have multiple issues and some years have no issues.

`--uncleaned_dir` : The directory where the uncleaned text files are located (these are csv format).

`--pdf_dir` : The directory where the PDF files are located.

`--out` : The output directory where the curated CSV file will be saved.

## Teething Problems

I have done this kind of thing before for work, and ill be amazed if there arent issues or that I have made oversights/ had blindspots. 

If anyone has any problems with the tool, please let me know and ill patch it asap.