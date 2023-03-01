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

visualization_types = ['pct missing value per col', 'modality decomposition per specie']

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
                ], style={'width': '48%'})
            
    ]),

    ## graphs
    dcc.Graph(id='main_plot')
])

# callback list
@app.callback(
    # output - visualizations
    Output('main_plot', 'figure'),
    # input - variables from dropdown/selected values
    [Input('metadata_fname', 'value')],
    [Input('viz_type', 'value')])

### function to update and generate visualizations
def update_graph(metadata_fname, viz_type):
    ### read in the data for selected quarter
    df = pd.read_csv(os.path.join(metadata_dir, metadata_fname), encoding='unicode_escape')

    # clean up data columns, column had 'CV' control value labels which we do not need. 
    # It complicates the column selection process
    df.columns = df.columns.str.replace(r"\([^)]*\)","").str.strip() # clean up data columns

    ### save the percentage of missing data report for plot
    pct_missing = pd.DataFrame({'pct_missing':df.isna().sum()*100/len(df)})
    pct_missing.reset_index(inplace = True)
    pct_missing = pct_missing.round({'pct_missing':4})

    ### drop columns with 90% missing data and more
    drop_list = pct_missing[pct_missing['pct_missing'] > 50]['index'].tolist()
    df = df.drop(drop_list, axis = 1) ### update df from here

    if 'missing' in viz_type:
        fig = px.bar(pct_missing, y='pct_missing', x='index', text='pct_missing',
            title="Percentage of missing data per column", width = 1500, height = 700)
        fig.update_layout(xaxis_title = "Column Name", yaxis_title = 'Percent Missing Value')
        fig.update_layout()
        return fig

    if 'modality' in viz_type:
        # group accordingly and get the count
        df['Species'] = df['Species'].str.lower() # convert everything to lowercase
        species_df = pd.DataFrame({'count':df.groupby(['Species', 'Modality']).size()}).sort_values('count').reset_index()

        # plot
        fig1 = px.bar(species_df, x="Species", y="count", color="Modality", text_auto=True,
                     title = "Modality Composition by Species",
                     height=700, width= 1800)
        fig1.update_layout(xaxis_title = "Species", yaxis_title = 'Sample Count')
        fig1.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'})
        fig1.update_layout()
        return fig1
 
## launch command
if __name__ == '__main__':
    app.run_server()
