from flask import Flask, request
import pandas as pd
import altair as alt
import numpy as np
alt.data_transformers.enable('default', max_rows=20000)
df = pd.read_pickle('/groups/inflation_viz/flaskapp/combined_data.pkl')
nest = df.set_index('series').dropna().to_dict()['Parent Series ID'] # Gives the series ID of the parent of a given series.
cat_names = df.set_index('series').dropna().to_dict()['Category'] # Gives the category name of a given series ID.

app = Flask(__name__)

def build_arg_text(**args):
    
    arg_text = '?chart_type=' + args.get('chart_type','Line+Chart')
    arg_text += '&start_year=' + args.get('start_year','2000')
    arg_text += '&end_year=' + args.get('end_year','2021')
    arg_text += '&inflation=' + args.get('inflation','By+Category')
    arg_text += '&earnings=' + args.get('earnings','Exclude')
    arg_text += '&unemployment=' + args.get('unemployment','Exclude')
    arg_text += '&stocks=' + args.get('stocks','Exclude')
    
    return arg_text

def data_parse(df, **args):
    
    print(args)

    website = 'https://apps-summer22.ischool.berkeley.edu/inflation_viz/chart'
    arg_text = website + build_arg_text(**args)
    
    start_date = '1/1/' + str(args.get('start_year','2000'))
    end_date = '12/1/' + str(args.get('end_year','2021'))
    
    # Start off with no hyperlinks and add where needed.
    df['href'] = arg_text
    
    # CPI
    df_cpi = pd.DataFrame(columns=['date','change','Category','href'])
    if args.get('parent','') == '':
        if args.get('inflation','By Category') == 'Exclude':
            df_cpi = pd.DataFrame(columns=['date','change','Category','href'])
        elif args.get('inflation','By Category') == 'By Category':
            df_cpi = df[df['Parent Series ID'] == 'CUSR0000SA0']
        elif args.get('inflation','By Category') == 'Total':
            df_cpi = df[df['series'] == 'CUSR0000SA0']
    else:
        df_cpi = df[df['Parent Series ID'] == args.get('parent','')]
        
    if args.get('inflation','By Category') != 'Exclude':
        #df_cpi['Category'] = 'CPI - ' + df_cpi['Category']
        df_cpi['href'] = np.where(df_cpi['Leaf'] == 0, arg_text + '&parent=' + df_cpi['series'], arg_text)
        
    # Earnings
    if args.get('earnings','') in ['','Exclude']:
        df_earnings = pd.DataFrame()
    else:
        df_earnings = df[(df['Type'] == 'Earnings') & (df['Bucket'] == args.get('earnings','').replace('+',' '))]
        
    # Unemployment
    if args.get('unemployment','') in ['','Exclude']:
        df_unemployment = pd.DataFrame()
    else:
        df_unemployment = df[(df['Type'] == 'Unemployment') & (df['Bucket'] == args.get('unemployment','').replace('+',' '))]
        
    # Stocks
    if args.get('stocks','') in ['','Exclude']:
        df_stocks = pd.DataFrame()
    else:
        df_stocks = df[df['Type'] == 'Stocks'] 

    # Combine selected data.
    df = pd.concat([df_cpi, df_earnings, df_unemployment, df_stocks])

    # Skip remaining steps if df is empty.
    if len(df) == 0:
        return df

    # Normalize values to % change in the specific category from start of date window.
    baseline_dict, ac_dict = {}, {}
    series_start_dt = df[['date','value','Category']].groupby('Category').date.min().to_dict()
    min_dt = df[df['year'] == start_year][['date','value','Category']].groupby('Category').date.min().to_dict()
    #for k,v in min_dt.items():
    #    min_dt[k] = max(v,pd.to_datetime(start_date))
    for k,v in min_dt.items():
        baseline_dict[k] = df[(df['Category'] == k) & (df['date'] == v)].value.item()
    df['baseline'] = df['Category'].map(baseline_dict) 
    df['change'] = df['value']/df['baseline'] - 1
    df['baseline_year'] = df['Category'].map(series_start_dt).dt.year
    df['partial_data'] = np.where(df['baseline_year'] > int(args.get('start_year','2000')), "Since " + df['baseline_year'].astype(str), "")

    # Looking up anual change
    cat_list = df['Category'].to_list()
    date_list = df['date'].to_list()
    val_list = df['value'].to_list()
    val_lookup = dict(zip(zip(cat_list,date_list), val_list))
    df['past_key']  = list(zip(df['Category'], df['date'] - pd.offsets.DateOffset(years=1)))
    df['past_val'] = df['past_key'].map(val_lookup)
    df['yoy_change'] = df['value'] / df['past_val'] - 1

    return df

def build_line(df, **args):
    
    # Set dates.
    start_year = args.get('start_year',2000)
    start_date = '1/1/' + str(start_year)
    end_year = args.get('end_year',2021)
    end_date = '12/1/' + str(end_year)
    
    # Create title.
    if end_year != start_year:
        c_title = 'Change ' + str(start_year) + ' to ' + str(end_year)
    else:
        c_title = 'Change during ' + str(start_year)
    
    # Set color scheme based on the number of categories.
    if len(df['Category'].unique()) > 10:
        c_scheme = 'category20'
    else:
        c_scheme = 'category10'
        
    # Check for hrefs.
    has_hrefs = len(df[df['href'] != 'None']) > 0
    has_non_hrefs = len(df[df['href'] == 'None']) > 0
    
    # Line Chart
    t_chart = alt.Chart(df[['date','change','Category','href']][(df['date'] >= start_date) & (df['date'] <= end_date) & (df['href'] != '')], title=c_title + ' by Category').mark_line(strokeWidth=2.5).encode(
            x = alt.X('date', title = 'Year'),
            y = alt.Y('change', title = c_title, axis=alt.Axis(format='%')),
            color = alt.Color('Category', scale=alt.Scale(scheme = c_scheme)),
            tooltip = 'Category',
            href = alt.Href('href')
        ).properties(height=400, width=600)
        
    t_chart['usermeta'] = {"embedOptions": {'loader': {'target': '_chart'}}}
    
    return t_chart

def build_bar(df, **args):
    
    # Set dates.
    start_year = int(args.get('start_year',2000))
    start_date = '1/1/' + str(start_year)
    end_year = int(args.get('end_year',2021))
    end_date = '12/1/' + str(end_year)
    
    # Create title.
    if end_year != start_year:
        c_title = 'Change ' + str(start_year) + ' to ' + str(end_year)
    else:
        c_title = 'Change during ' + str(start_year)
    
    # Set color scheme based on the number of categories.
    if len(df['Category'].unique()) > 10:
        c_scheme = 'category20'
    else:
        c_scheme = 'category10'
        
    # Bar Chart
    t_chart = alt.Chart(df[['date','change','Category','href','partial_data']][(df['date'] == end_date) | ((df['periodName'] == '4th Quarter') & (df['year'] == end_year))]).mark_bar().encode(
            x = alt.X('Category', sort='y', axis=alt.Axis(labels=False)),
            y = alt.Y('change', title=c_title, axis=alt.Axis(format='%')),
            color = alt.Color('Category', scale=alt.Scale(scheme = c_scheme)),
            tooltip = [alt.Tooltip('date:T', title = 'Date', format='%B %Y'), 'Category',
                   alt.Tooltip('change:Q',title = "Total Change",  format='.1%'), 
                   alt.Tooltip('partial_data',title = "Notes")],
            href = alt.Href('href')
        ).properties(height=400, width=600)
    
    
    t_chart['usermeta'] = {"embedOptions": {'loader': {'target': '_chart'}}}
    
    return t_chart

def build_line_v2(df, **args):
    
    # Set dates.
    start_year = args.get('start_year',2000)
    start_date = '1/1/' + str(start_year)
    ar_start_year = '1/1/' + str(int(start_year) - 1)
    end_year = args.get('end_year',2021)
    end_date = '12/1/' + str(end_year)
    
    # Create title.
    if end_year != start_year:
        c_title = 'Change ' + str(start_year) + ' to ' + str(end_year)
    else:
        c_title = 'Change during ' + str(start_year)

    df_test = df.loc[(df['date'] >= ar_start_year) & (df['date'] <= end_date)]
    
    # new data frame with only graph values
    graph_data = df_test[['date', 'Category', 'change','yoy_change', 'href']]
    graph_data['change'] = graph_data['change'].round(decimals = 3)
    graph_data['yoy_change'] = graph_data['yoy_change'].round(decimals = 3)
    graph_data = graph_data[graph_data['date'] >= start_date]
    
    s2 = pd.DataFrame(graph_data.Category.unique(), columns = ['Category'])
    highlight = alt.selection_multi(on = 'mouseover', fields=['Category'], nearest = True)

    line = alt.Chart(graph_data).mark_line(interpolate = 'basis').encode(
        x = alt.X('date:T', title = "Year"),
        y = alt.Y('change:Q', title = c_title, axis=alt.Axis(ticks = False, domain = False, format='%')),
        tooltip = [alt.Tooltip('date:T', title = 'Date', format='%B %Y'), 'Category',
                   alt.Tooltip('change:Q',title = "Cumulative Change",  format='.1%'), 
                   alt.Tooltip('yoy_change:Q',title = "Annual Change",  format='.1%')],    
        color = alt.Color('Category:N'),
        href = alt.Href('href'),
        opacity = alt.condition(highlight, alt.value(1), alt.value(0.2))).properties(
        width=600, height=500
    )

    hover_legend = alt.Chart(s2).mark_circle(size = 100).encode(
        y = alt.Y('Category:N', axis = alt.Axis(orient = 'right', domain = False, ticks = False), title = None),
        color = alt.Color('Category:N', legend = None),
        opacity = alt.condition(highlight, alt.value(1), alt.value(0.2))
    ).add_selection(
        highlight
    )
    
    t_chart = (line | hover_legend).configure_axis(
        grid=False).configure_view(
        strokeWidth = 0)
    
    
    t_chart['usermeta'] = {"embedOptions": {'loader': {'target': '_chart'}}}
    
    return t_chart

@app.route("/learn")
def learn_page():
    learn_html = """
    <html>
    <head>
        <style>
        body {
        font: 1em sans-serif;
        }

        /* sidebar menu */
        .sidenav {
            height: 100%;
            width: 170px;
            position: fixed;
            z-index: 1;
            top: 0;
            left: 0;
            background-color: #F7F3F3;
            overflow-x: hidden;
            padding-top: 50px;
        }
        /* nav menu links */
        .sidenav a {
            padding: 6px 8px 6px 20px;
            text-decoration: none;
            font-size: 18px;
            color: #030303;
            display: block;
        }
        /* link hover effect */
        .sidenav a:hover {
            color: #AC0A0A;
        }
        .sidenav img {
            padding: 6px 8px 6px 20px;
        }
        .main {
            margin-left: 170px;
            padding: 0px 10px;
        }
        </style>
    </head>
    <body>
        <div class="sidenav">
            <img src="https://www.ischool.berkeley.edu/sites/default/files/berkeleyischool-logo-modified-blue.svg" width="120" height="68" padding/>
            <br>
            <br>
            <a href="https://apps-summer22.ischool.berkeley.edu/inflation_viz/learn" style="color: #AC0A0A">Learn</a>
            <a href="https://apps-summer22.ischool.berkeley.edu/inflation_viz/">Explore</a>
            <a href="#">Build for me</a>
        </div>

        <div class="main">
            <h2>About this website</h2>
            <p>This data visualization illustrates the rate of change for <a href="https://www.bls.gov/cpi/">consumer prices</a> and other economic data have changed over a specified period. The data is <a href="https://www.dallasfed.org/research/basics/indexing.aspx">indexed</a> to a common starting point (e.g., year 2000) and a common ending point (e.g., year 2021) to show how much each measurement has changed over the chosen timeframe as a percentage.</p> 
            <p>The consumer price data can be viewed as a total aggregate figure or it can be separated into major expenditure categories, such as health and food. An increase in consumer prices represents a period of inflation, while a decline represents a period of deflation.</p>
            <p>Similarly, the other data can be viewed as a total aggregate or by categories. For instance, the <a href="https://www.bls.gov/cps/earnings.htm">earnings data</a> and <a href="https://www.bls.gov/cps/lfcharacteristics.htm#unemp">unemployment data</a> can be separated by gender (male / female), race or education level. The <a href="https://www.google.com/finance/markets/indexes?hl=en">stocks data</a> represents information for several major US stock indexes.</p>   

            <h2>How we thought about this tool</h2>
            <p>This text will describe more about the website and data sources.</p>

            <h2>Credits</h2>
            <p>This website was created by:</p>
            <ul>
                <li>Pedro Belotti</li>
                <li>Steven Hewitt</li>
                <li>Emily Huang</li>
                <li>Nathan Martinez</li>
                <li>Giulia Olsson</li>
            </ul>
        </div>
    </body>
    </html>

    """

    return learn_html


@app.route("/")
def main_page():
    main_html = """
<html>
<head>
<style>
body {
  font: 1em sans-serif;
}

form {
  margin: 0 auto;
  width: 360px;
  padding: 1em;
  border: 1px solid #CCC;
  border-radius: 1em;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

form li + li {
  margin-top: 1em;
}

label {
  display: inline-block;
  width: 150px;
  text-align: right;
}

select,
textarea {
  font: 1em sans-serif;

  width: 200px;
  box-sizing: border-box;

  border: 1px solid #999;
}

input:focus,
textarea:focus {
  border-color: #000;
}

textarea {
  vertical-align: top;

  height: 5em;

}

.button {
  padding-left: 150px;
}

button {
  margin-left: .5em;
}

/* sidebar menu */
.sidenav {
    height: 100%;
    width: 170px;
    position: fixed;
    z-index: 1;
    top: 0;
    left: 0;
    background-color: #F7F3F3;
    overflow-x: hidden;
    padding-top: 50px;
}

/* nav menu links */
.sidenav a {
    padding: 6px 8px 6px 20px;
    text-decoration: none;
    font-size: 18px;
    color: #030303;
    display: block;
}

/* link hover effect */
.sidenav a:hover {
    color: #AC0A0A;
}

.sidenav img {
    padding: 6px 8px 6px 20px;
}

.main {
    margin-left: 170px;
    padding: 0px 10px;
}

</style>
</head>
<body>

<div class="sidenav">
    <img src="https://www.ischool.berkeley.edu/sites/default/files/berkeleyischool-logo-modified-blue.svg" width="120" height="68" padding/>
    <br>
    <br>
    <a href="https://apps-summer22.ischool.berkeley.edu/inflation_viz/learn">Learn</a>
    <a href="https://apps-summer22.ischool.berkeley.edu/inflation_viz/" style="color: #AC0A0A">Explore</a>
    <a href="#">Build for me</a>
</div>

<div class="main">


<h2>Instructions</h2>
<p>To use this tool, the following steps should be taken:</p>
<ol>
  <li>Select the type of graph (line graph or bar chart).</li>
  <li>Select a start and end year from the drop-down menus.</li>
  <li>In the inflation drop-down menu, select whether you would like to view top-line inflation for all consumer goods or by all major expenditure categories</li>
  <li>In the remaining drop-down menus, you have to option to view additional data about earnings, unemployment, or stocks.</li>
</ol>

<table>
<tr>
<td>
<iframe src="https://apps-summer22.ischool.berkeley.edu/inflation_viz/chart" name="_chart" width="900" height="550" frameBorder="0"></iframe>
</td>
<td valign="top">
<form action="https://apps-summer22.ischool.berkeley.edu/inflation_viz/chart" method="get" target="_chart">
 <ul>

  <li>
    <label for = "chart_type">Chart Type:</label>
    <select name = "chart_type" id="chart_type">
      <option value = "Line Chart" selected>Line Chart</option>
      <option value = "Bar Chart">Bar Chart</option>
    </select>
  </li>

  <li>
    <label for = "start_year">Start Year:</label>
    <select name = "start_year" id="start_year">
      <option value = "1970">1970</option>
      <option value = "1971">1971</option>
      <option value = "1972">1972</option>
      <option value = "1973">1973</option>
      <option value = "1974">1974</option>
      <option value = "1975">1975</option>
      <option value = "1976">1976</option>
      <option value = "1977">1977</option>
      <option value = "1978">1978</option>
      <option value = "1979">1979</option>
      <option value = "1980">1980</option>
      <option value = "1981">1981</option>
      <option value = "1982">1982</option>
      <option value = "1983">1983</option>
      <option value = "1984">1984</option>
      <option value = "1985">1985</option>
      <option value = "1986">1986</option>
      <option value = "1987">1987</option>
      <option value = "1988">1988</option>
      <option value = "1989">1989</option>
      <option value = "1990">1990</option>
      <option value = "1991">1991</option>
      <option value = "1992">1992</option>
      <option value = "1993">1993</option>
      <option value = "1994">1994</option>
      <option value = "1995">1995</option>
      <option value = "1996">1996</option>
      <option value = "1997">1997</option>
      <option value = "1998">1998</option>
      <option value = "1999">1999</option>
      <option value = "2000" selected>2000</option>
      <option value = "2001">2001</option>
      <option value = "2002">2002</option>
      <option value = "2003">2003</option>
      <option value = "2004">2004</option>
      <option value = "2005">2005</option>
      <option value = "2006">2006</option>
      <option value = "2007">2007</option>
      <option value = "2008">2008</option>
      <option value = "2009">2009</option>
      <option value = "2010">2010</option>
      <option value = "2011">2011</option>
      <option value = "2012">2012</option>
      <option value = "2013">2013</option>
      <option value = "2014">2014</option>
      <option value = "2015">2015</option>
      <option value = "2016">2016</option>
      <option value = "2017">2017</option>
      <option value = "2018">2018</option>
      <option value = "2019">2019</option>
      <option value = "2020">2020</option>
      <option value = "2021">2021</option>
    </select>
  </li>

  <li>
    <label for = "end_year">End Year:</label>
    <select name = "end_year" id="end_year">
      <option value = "1970">1970</option>
      <option value = "1971">1971</option>
      <option value = "1972">1972</option>
      <option value = "1973">1973</option>
      <option value = "1974">1974</option>
      <option value = "1975">1975</option>
      <option value = "1976">1976</option>
      <option value = "1977">1977</option>
      <option value = "1978">1978</option>
      <option value = "1979">1979</option>
      <option value = "1980">1980</option>
      <option value = "1981">1981</option>
      <option value = "1982">1982</option>
      <option value = "1983">1983</option>
      <option value = "1984">1984</option>
      <option value = "1985">1985</option>
      <option value = "1986">1986</option>
      <option value = "1987">1987</option>
      <option value = "1988">1988</option>
      <option value = "1989">1989</option>
      <option value = "1990">1990</option>
      <option value = "1991">1991</option>
      <option value = "1992">1992</option>
      <option value = "1993">1993</option>
      <option value = "1994">1994</option>
      <option value = "1995">1995</option>
      <option value = "1996">1996</option>
      <option value = "1997">1997</option>
      <option value = "1998">1998</option>
      <option value = "1999">1999</option>
      <option value = "2000">2000</option>
      <option value = "2001">2001</option>
      <option value = "2002">2002</option>
      <option value = "2003">2003</option>
      <option value = "2004">2004</option>
      <option value = "2005">2005</option>
      <option value = "2006">2006</option>
      <option value = "2007">2007</option>
      <option value = "2008">2008</option>
      <option value = "2009">2009</option>
      <option value = "2010">2010</option>
      <option value = "2011">2011</option>
      <option value = "2012">2012</option>
      <option value = "2013">2013</option>
      <option value = "2014">2014</option>
      <option value = "2015">2015</option>
      <option value = "2016">2016</option>
      <option value = "2017">2017</option>
      <option value = "2018">2018</option>
      <option value = "2019">2019</option>
      <option value = "2020">2020</option>
      <option value = "2021" selected>2021</option>
    </select>
  </li>

  <li>
    <label for = "inflation">Inflation (CPI):</label>
    <select name = "inflation" id="inflation">
      <option value = "Exclude">Exclude</option>
      <option value = "By Category" selected>By Category</option>
      <option value = "Total">Total</option>
    </select>
  </li>

  <li>
    <label for = "earnings">Earnings:</label>
    <select name = "earnings" id="earnings">
      <option value = "Exclude" selected>Exclude</option>
      <option value = "Total">Total</option>
      <option value = "By Education">By Education</option>
      <option value = "By Gender">By Gender</option>
      <option value = "By Race">By Race</option>
      <option value = "By Race and Gender">By Race and Gender</option>
    </select>
  </li>

  <li>
    <label for = "unemployment">Unemployment:</label>
    <select name = "unemployment" id="unemployment">
      <option value = "Exclude" selected>Exclude</option>
      <option value = "Total">Total</option>
      <option value = "By Education">By Education</option>
      <option value = "By Gender">By Gender</option>
      <option value = "By Race">By Race</option>
    </select>
  </li>

  <li>
    <label for = "stocks">Stock Markets:</label>
    <select name = "stocks" id="stocks">
      <option value = "Exclude" selected>Exclude</option>
      <option value = "Include">Include</option>
    </select>
  </li>

  <li class="button">
    <button type="submit">Build Chart</button>
  </li>
</td>
</tr></table>
<p><i>CPI series marked with an asterisk (*) have not been adjusted for normal seasonal variations in pricing due to a lack of available data.</i></p>
</div>
</body>
</html>

    """
    return main_html

@app.route("/chart")
def chart_render():
    
    # Parse arguments.
    args = request.args.to_dict()  
    
    # Check to see if all datatypes are being excluded.
    if args.get('inflation','By Category') == 'Exclude' and args.get('earnings','Exclude') == 'Exclude' and args.get('unemployment','Exclude') == 'Exclude' and args.get('stocks','Exclude') == 'Exclude':
        return '<font color="red">Error: No data to display. Please try different chart settings.</font>'

    # Check for date mismatch.
    if int(args.get('start_year',2000)) > int(args.get('end_year',2021)):
        return '<font color="red">Error: No data to display. Please try different chart settings.</font>'

    # Fetch data.
    t_df = data_parse(df.copy(deep=True), **args)
    
    # Check for blank DataFrame.
    if len(t_df) == 0:
        return '<font color="red">Error: No data to display. Please try different chart settings.</font>'

    if args.get('chart_type','Line Chart') == 'Line Chart':
        out_html = build_line(t_df, **args)
        pass
    elif args.get('chart_type','') == 'Bar Chart':
        out_html = build_bar(t_df, **args)
    else:
        return ''
    
    return out_html.to_html(embed_options={"actions":False})

if __name__ == "__main__":
    app.run()