import pandas as pd
import numpy as np
import os, glob
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go

app = Dash(__name__) # initiate the dashboard

cwd = os.getcwd() # current work directory
data_dir = os.path.join(cwd, "BCDC-Metadata")
metadata_dir = os.path.join(data_dir, 'Sample-Inventory')

metadata_filenames = []
for file in os.listdir(metadata_dir):
    if file.endswith('csv'):
        metadata_filenames.append(file)

panel_options = {
    'Cell and Sample Counts':['Cumulative', 'Modality', 'Grant']
}


visualization_types = ['Percentage of Missing Values Per Column', 'Cell and Sample Counts']

### dashboard layout
app.layout = html.Div([
    ## headers
    html.H1(children='Sample Dashboard - BCDC Metadata'),
    html.Div(children='''
       The data used for analysis was retrieved from the BCDC-Metadata repo. It only includes the Metadata files in the 'Sample-Inventory' directory for the time being.
    '''),
    html.Div(children='''
    link to repository: https://github.com/BICCN/BCDC-Metadata/tree/BCDC-schema-v2/Sample-Inventory
     '''),
    html.Br(),

    ## dropdowns
    html.Div([
        # first dropdown - activity type
        html.Div([
            html.Label(['Metadata File Name'], style={'font-weight': 'bold', "text-align": "center"}),
            dcc.Dropdown(
                metadata_filenames, 
                metadata_filenames[0], # default value
                id='metadata_fname')
                ], style={'width': '48%', 'display': 'inline-block'}),
        html.Br(), # some blank space
        # second dropdown - sensors to display
        html.Div([
            html.Label(['Visualization Type'], style={'font-weight': 'bold', "text-align": "center"}),
            dcc.Dropdown(
                visualization_types,
                visualization_types[0],
                id='viz_type')
                ], style={'width': '48%'}),
        html.Br(),
        html.Div([
            html.Label(['Select Quarters'], style={'font-weight': 'bold', "text-align": "center"}),
            dcc.Dropdown(
                id='quarters', multi=True)], style={'width': '48%'}),
        html.Br(),
        html.Div([
            dcc.Dropdown(
                id = 'subcategory')], style= {'display': 'block', 'width': '48%'}),
        html.Br(),
        html.Div([
        dcc.RadioItems(
            ['Specimen Types', 'Technique'],
            'Specimen Types',
            id='meas_types')
            ], style={'width': '48%', 'display': 'block'})
    ]),
    ## graphs
    dcc.Graph(id='main_plot')
])

#### callback functions
### function to update available quarters
@app.callback( # update options based on df
    Output('quarters', 'options'),
    Input('metadata_fname', 'value'))
def get_avail_quarters(fname):
    list_all = pd.read_csv(os.path.join(metadata_dir, fname), encoding='unicode_escape')['Metadata Submission'].dropna().unique()
    quarter_names = list(filter(lambda x : 'Q' in x, list_all))
    return quarter_names

## get the above option into value
@app.callback(
    Output('quarters', 'value'),
    [Input('quarters', 'options')])
def set_quarter(quarter):
    return quarter

### function to update subcategories
@app.callback(
    Output('subcategory', 'style'),
    Input('viz_type', 'value'))
def show_hide(viz_type):
    if 'Missing Values' in viz_type:
        return {'display': 'none'}
    else:
        return {'display': 'block'}

## function to get list of subcategories per type  
@app.callback(
    Output('subcategory', 'options'),
    Input('viz_type', 'value'))
def set_subcat_options(viz_type):
    return panel_options[viz_type] # get the dictionary with subcategories of according category

## function to update selected subcategory
@app.callback(
    Output('subcategory', 'value'),
    Input('subcategory', 'options'))
def set_subcat_value(subcategory):
    return subcategory

### function to update measure types
@app.callback(
    Output('meas_types', 'style'),
    Input('viz_type', 'value'))
def show_hide(viz_type):
    if 'Missing Values' in viz_type:
        return {'display': 'none'}
    else:
        return {'display': 'block'}
    
## get the measure types into value
@app.callback(
    Output('meas_types', 'value'),
    [Input('meas_types', 'options')])
def set_quarter(meas_types):
    return meas_types

### main callbacks into the update_graph() function
@app.callback(
    # output - visualizations
    Output('main_plot', 'figure'),
    # input - variables from dropdown/selected values
    [Input('metadata_fname', 'value')],
    [Input('viz_type', 'value')],
    [Input('quarters', 'value')],
    Input('subcategory', 'value'),
    Input('meas_types', 'value'))


### function to update and generate visualizations
def update_graph(metadata_fname, viz_type, quarters, subcategory, meas_types):
    ### read in the data for selected quarter
    df = pd.read_csv(os.path.join(metadata_dir, metadata_fname), encoding='unicode_escape')
    # get only the selected quarters
    df = df[df['Metadata Submission'].isin(quarters)]
    
    # clean up data columns, column had 'CV' control value labels which we do not need. 
    # It complicates the column selection process
    df.columns = df.columns.str.replace(r"\([^)]*\)","").str.strip() # clean up data columns
    df['Subspecimen Type'] = df['Subspecimen Type'].str.lower() # caps


    ### save the percentage of missing data report for plot
    pct_missing = pd.DataFrame({'pct_missing':df.isna().sum()*100/len(df)})
    pct_missing.reset_index(inplace = True)
    pct_missing = pct_missing.round({'pct_missing':4})

    ### drop columns with 90% missing data and more
    drop_list = pct_missing[pct_missing['pct_missing'] > 50]['index'].tolist()
    df = df.drop(drop_list, axis = 1) ### update df from here

    if 'Missing Values' in viz_type:
        fig_missing_vals = px.bar(pct_missing, y='pct_missing', x='index', text='pct_missing',
            title="Percentage of missing data per column", width = 1500, height = 700)
        fig_missing_vals.update_layout(xaxis_title = "Column Name", yaxis_title = 'Percent Missing Value')
        fig_missing_vals.update_layout()
        return fig_missing_vals
    
    if 'Counts' in viz_type:
        if 'Grant' in subcategory:
            if meas_types == 'Specimen Types':
                grant_df = pd.DataFrame({'count':df.groupby(['Grant Number', 'Subspecimen Type']).size()}).sort_values('count').reset_index()
                grant_fig = px.bar(grant_df, x="Subspecimen Type", y="count", color = 'Grant Number', text_auto=True,
                            title = "Specimen Type Composition Per Grant",
                            height=700, width= 1800)
                grant_fig.update_layout(xaxis_title = "Subspecimen Type", yaxis_title = 'Sample Count')
            if meas_types == 'Technique':
                grant_df = pd.DataFrame({'count':df.groupby(['Grant Number', 'Technique']).size()}).sort_values('count').reset_index()
                grant_fig = px.bar(grant_df, x="Technique", y="count", color = 'Grant Number', text_auto=True,
                            title = "Technique Composition Per Grant",
                            height=700, width= 1800)
                grant_fig.update_layout(xaxis_title = "Technique", yaxis_title = 'Sample Count')
            grant_fig.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'})
            grant_fig.update_layout()
            return grant_fig


        if 'Modality' in subcategory:
            # group accordingly and get the count
            #df['Species'] = df['Species'].str.lower() # convert everything to lowercase
            if meas_types == 'Specimen Types':
                mod_df = pd.DataFrame({'count':df.groupby(['Subspecimen Type', 'Modality']).size()}).sort_values('count').reset_index()
                # plot
                modality_fig = px.bar(mod_df, x="Subspecimen Type", y="count", color="Modality", text_auto=True,
                        title = "Modality Composition by Subspecimen Type",
                        height=700, width= 1800)
                modality_fig.update_layout(xaxis_title = "Subspecimen Type", yaxis_title = 'Sample Count')
            if meas_types == 'Technique':
                mod_df = pd.DataFrame({'count':df.groupby(['Technique', 'Modality']).size()}).sort_values('count').reset_index()
                modality_fig = px.bar(mod_df, x="Technique", y="count", color="Modality", text_auto=True,
                        title = "Modality Composition by Techniques",
                        height=700, width= 1800)
                modality_fig.update_layout(xaxis_title = "Techniques", yaxis_title = 'Sample Count')


            modality_fig.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'})
            modality_fig.update_layout()
            return modality_fig
        
        if 'Cumulative' in subcategory:
            if meas_types == 'Specimen Types':
                overall_df = pd.DataFrame({'count':df.groupby(['Subspecimen Type']).size()}).sort_values('count').reset_index()
                overall_fig = px.bar(overall_df, x="Subspecimen Type", y="count", text_auto=True,
                        title = "Cumulative Sample Counts per Specimen Type",
                        height=700, width= 1800)
                overall_fig.update_layout(xaxis_title = "Subspecimen Type", yaxis_title = 'Sample Count')
            if meas_types == 'Technique':
                overall_df = pd.DataFrame({'count':df.groupby(['Technique']).size()}).sort_values('count').reset_index()
                overall_fig = px.bar(overall_df, x="Technique", y="count", text_auto=True,
                        title = "Cumulative Sample Counts per Techniques",
                        height=700, width= 1800)
            overall_fig.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'})
            overall_fig.update_layout(xaxis_title = "Techniques", yaxis_title = 'Sample Count')
            overall_fig.update_layout()
            return overall_fig

    
## launch command
if __name__ == '__main__':
    app.run_server()


