# Inflation Trends and Related Economic Data

UC Berkeley School of Information<br>
Data Visualization and Communication (W209)<br>
Final Project<br>

Project Participants:
<ul><li>Pedro Belotti</li>
<li>Steve Hewitt</li>
<li>Emily Huang</li>
<li>Nathan Martinez</li>
<li>Giulia Olsson</li></ul><br>

https://apps-summer22.ischool.berkeley.edu/inflation_viz/<br>

The codebase in this repository corresponds to the live version of our project website.

### Repo Contents
    ├── Final_Data                                 <- Code to pull and combine data.
        ├── CPI_Category_Tree_Final - REVISED.xlsx      <- Input table of CPI categories to pull from BLS API and assocaited metadata.
        ├── Final_Data_Pull.ipynb                       <- Code to combine multiple BLS API pulls and flat file to create final dataset.
        ├── Other_BLS_Data_Final - REVISED.xlsx         <- Input table of of non-CPI categories to pull from BLS API and assocaited metadata.
        ├── Stock_Markets_Data - REVISED.xlsx           <- Stock market historical pricing from Google Finance.
        ├── combined_data.pkl                           <- Final dataset for website.
    ├── Flask                                      <- Code to produce website.
        ├── Simulated_Flask_Test_Args.ipynb             <- Prototyping tool for chart updates.
        └── flaskapp.py                                 <- Website script for Flask app.
    └── README.md                                  <- Overiew of repo contents.
