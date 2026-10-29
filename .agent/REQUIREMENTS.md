## Purpose

Build a reproducible tool that collects publicly accessible policy text from New Zealand political party websites supplied by the user, analyses the language used, and generates a separate word cloud for each party.

The tool is intended for exploratory civic research. Word clouds and term rankings describe patterns in the collected text; they do not establish a party's intent, the quality of its policies, or the likely effects of those policies.


# Goals 
1. Gather policy data for the New Zealand Political parties only, for National, Labour, Greens, ACT, NZ First, Te Pati Maori, The Opportunities Party, Aotearoa Legalise Cannabis Party
1. Fetch each starting page from the below list , and discover links directly linked from that page to gather information
    - National - https://www.national.org.nz/plan
    - Labour - https://www.labour.org.nz/our-policies
    - Greens - https://www.greens.org.nz/policy
    - ACT - https://www.act.org.nz/policies
    - NZ First - https://www.nzfirst.nz/policy
    - Te Pati Maori - https://www.maoriparty.org.nz/policy
    - The Opportunities Party - https://www.opportunity.org.nz/policy
    - Aotearoa Legalise Cannabis Party - https://www.alcp.org.nz/policy
1. Follow only eligible first-level links within the same website/domain scope.
1. Extract readable page text while excluding obvious navigation and boilerplate where possible.
1. preserve source URLs and enough collection metadata to audit the material used.
1. Clean text and calculate two term rankings:
   - raw frequency after configured stop-word removal;
   - TF-IDF, to highlight terms that are relatively distinctive across the included party corpora.
1. Generate a PNG word cloud for each party from its selected top 20 terms.
1. Save CSV data and extracted text/source records.
1. Run locally in a Jupyter notebook, with clear outputs, progress, and error reporting.
1. Create a shell script that can be used to run the Jupyter Notebook from command line, in the project's home directory
1. Add a section in the README.md, on 
    - how to install on local machine from the github repo
    - how to run the Jupyter notebook, after installing
    - Add a highlighted item to say this is only for Apple Silicon M1 and above, MacOS Tahoe
    - Document dependency and environment instructions in this section.


