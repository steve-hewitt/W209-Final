from flask import Flask, request
import pandas as pd
import altair as alt
import numpy as np
alt.data_transformers.enable('default', max_rows=20000)
df = pd.read_pickle('combined_data.pkl')
nest = df.set_index('series').dropna().to_dict()['Parent Series ID'] # Gives the series ID of the parent of a given series.
cat_names = df.set_index('series').dropna().to_dict()['Category'] # Gives the category name of a given series ID.

app = Flask(__name__)

def build_arg_text(**args):
    
    arg_text = '?chart_type=' + args.get('chart_type','Line+Chart')
    arg_text += '&start_year=' + args.get('start_year','2000')
    arg_text += '&inflation=' + args.get('inflation','By_Category')
    arg_text += '&earnings=' + args.get('earnings','Exclude')
    arg_text += '&unemployment=' + args.get('unemployment','Exclude')
    arg_text += '&stocks=' + args.get('stocks','Exclude')
    arg_text += '&interest=' + args.get('interest','Exclude')
    
    return arg_text

def data_parse(df, **args):
    
    website = 'chart.html'
    arg_text = website + build_arg_text(**args)
    
    start_date = '1/1/' + str(args.get('start_year','2000'))
    end_date = '12/1/' + str(args.get('end_year','2021'))
    
    # Start off with no hyperlinks and add where needed.
    df['href'] = arg_text
    
    # CPI
    if args.get('parent','') == '':
        if args.get('inflation','By+Category') == 'Exclude':
            df_cpi = pd.DataFrame
        elif args.get('inflation','By+Category') == 'By+Category':
            df_cpi = df[df['Parent Series ID'] == 'CUSR0000SA0']
        elif args.get('inflation','By+Category') == 'Total':
            df_cpi = df[df['series'] == 'CUSR0000SA0']
    else:
        df_cpi = df[df['Parent Series ID'] == args.get('parent','')]
        
    if args.get('inflation','By+Category') != 'Exclude':
        df_cpi['Category'] = 'CPI - ' + df_cpi['Category']
        df_cpi['href'] = np.where(df_cpi['Leaf'] == 0, arg_text + '&parent=' + df_cpi['series'], 'None')
        
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
        
    # Interest
    if args.get('interest','') in ['','Exclude']:
        df_interest = pd.DataFrame()
    else:
        df_interest = df[df['Type'] == 'Interest'] 

    # Combine selected data.
    df = pd.concat([df_cpi, df_earnings, df_unemployment, df_stocks, df_interest])

    # Normalize values to % change the specific category from start of date window.
    baseline_dict = {}
    min_dt = df[['date','value','Category']].groupby('Category').date.min().to_dict()
    for k,v in min_dt.items():
        min_dt[k] = max(v,pd.to_datetime(start_date))
    for k,v in min_dt.items():
        baseline_dict[k] = df[(df['Category'] == k) & (df['date'] == v)].value.item()
    df['baseline'] = df['Category'].map(baseline_dict) 
    df['change'] = df['value']/df['baseline'] - 1

    return df

def build_line(df, **args):
    
    # Set dates.
    start_year = args.get('start_year',2000)
    start_date = '1/1/' + str(start_year)
    end_year = args.get('end_year',2021)
    end_date = '12/1/' + str(end_year)
    
    # Set color scheme based on the number of categories.
    if len(df['Category'].unique()) > 10:
        c_scheme = 'category20'
    else:
        c_scheme = 'category10'
        
    # Check for hrefs.
    has_hrefs = len(df[df['href'] != 'None']) > 0
    has_non_hrefs = len(df[df['href'] == 'None']) > 0
    
    # Line Chart
    t_chart = alt.Chart(df[['date','change','Category','href']][(df['date'] >= start_date) & (df['date'] <= end_date) & (df['href'] != '')], title='Change Since ' + str(start_year) +' by Category').mark_line().encode(
            x = alt.X('date', title = 'Year'),
            y = alt.Y('change', title='Change Since ' + str(start_year), axis=alt.Axis(format='%')),
            color = alt.Color('Category', scale=alt.Scale(scheme = c_scheme)),
            tooltip = 'Category',
            href = alt.Href('href')
        ).properties(height=400, width=600)
        
    t_chart['usermeta'] = {"embedOptions": {'loader': {'target': '_chart'}}}
    
    return t_chart

def build_bar(t_df, **args):
    
    # Set dates.
    start_date = '1/1/' + str(args.get('start_year','2000'))
    end_date = '12/1/' + str(args.get('end_year','2000'))
    
    # Set color scheme based on the number of categories.
    if len(df['Category'].unique()) > 10:
        c_scheme = 'category20'
    else:
        c_scheme = 'category10'
        
    # Bar Chart
    t_chart = alt.Chart(df[['date','change','Category','href']][(df['date'] == end_date) | ((df['periodName'] == '4th Quarter') & (df['year'] == end_year))],title='Change Since ' + str(start_year) + ' by Category').mark_bar().encode(
            x = alt.X('Category', sort='y'),
            y = alt.Y('change', title='Change Since ' + str(start_year), axis=alt.Axis(format='%')),
            color = alt.Color('Category', scale=alt.Scale(scheme = c_scheme)),
            tooltip = 'Category',
            href = alt.Href('href')
        ).properties(height=400, width=600)
    
    t_chart['usermeta'] = {"embedOptions": {'loader': {'target': '_chart'}}}
    
    return t_chart

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
  /* Center the form on the page */
  margin: 0 auto;
  width: 330px;
  /* Form outline */
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
  /* Uniform size & alignment */
  display: inline-block;
  width: 120px;
  text-align: right;
}

select,
textarea {
  /* To make sure that all text fields have the same font settings
     By default, textareas have a monospace font */
  font: 1em sans-serif;

  /* Uniform text field size */
  width: 200px;
  box-sizing: border-box;

  /* Match form field borders */
  border: 1px solid #999;
}

input:focus,
textarea:focus {
  /* Additional highlight for focused elements */
  border-color: #000;
}

textarea {
  /* Align multiline text fields with their labels */
  vertical-align: top;

  /* Provide space to type some text */
  height: 5em;
}

.button {
  /* Align buttons with the text fields */
  padding-left: 90px; /* same size as the label elements */
}

button {
  /* This extra margin represent roughly the same space as the space
     between the labels and their text fields */
  margin-left: .5em;
}

</style>
</head>
<body>

<img src="https://www.ischool.berkeley.edu/sites/all/themes/custom/i_school/images/logos/berkeleyischool-logo-blue.svg" width="320" height="133" />

<p>Replace me with all kinds of amazing supporting text.</p>

<table>
<tr>
<td>
<iframe src="chart.html" name="_chart" width="800" height="500" frameBorder="0"></iframe>
</td>
<td>
<form action="chart.html" method="get" target="_chart">
 <ul>

  <li>
    <label for = "chart_type">Chart Type:</label>
    <select name = "chart_type" id="chart_type">
      <option value = "Line Chart">Line Chart</option>
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
      <option value = "2021">2021</option>
    </select>
  </li>

  <li>
    <label for = "inflation">Inflation:</label>
    <select name = "inflation" id="inflation">
      <option value = "Exclude">Exclude</option>
      <option value = "By Category">By Category</option>
      <option value = "Total">Total</option>
    </select>
  </li>

  <li>
    <label for = "earnings">Earnings:</label>
    <select name = "earnings" id="earnings">
      <option value = "Exclude">Exclude</option>
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
      <option value = "Exclude">Exclude</option>
      <option value = "Total">Total</option>
      <option value = "By Education">By Education</option>
      <option value = "By Gender">By Gender</option>
      <option value = "By Race">By Race</option>
    </select>
  </li>

  <li>
    <label for = "stocks">Stock Markets:</label>
    <select name = "stocks" id="stocks">
      <option value = "Exclude">Exclude</option>
      <option value = "Include">Include</option>
    </select>
  </li>

  <li>
    <label for = "interest">Fed Interest Rate:</label>
    <select name = "interest" id="interest">
      <option value = "Exclude">Exclude</option>
      <option value = "Include">Include</option>
    </select>
  </li>

  <li class="button">
    <button type="submit">Build Chart</button>
  </li>
</td>
</tr></table>
</body>
</html>

    """
    return main_html

@app.route("/chart.html")
def join_a_guild():
    args = request.args
    
    t_df = data_parse(df.copy(deep=True), **args)

    if args['chart_type'] == 'Line+Chart':
        out_html = build_line(t_df, **args)
        pass
    elif args['chart_type'] == 'Bar+Chart':
        out_html = build_bar(t_df, **args)
    else:
        return ''
    
    return out_html