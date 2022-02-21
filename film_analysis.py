import streamlit as st
import pandas as pd
import numpy as np
from google.oauth2 import service_account
import gspread


def getgsheet(spreadsheet_url, sheet_num):
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )
    client = gspread.authorize(credentials)
    gsheet = client.open_by_url(spreadsheet_url).get_worksheet(sheet_num)

    return gsheet


def gsheet2df(gsheet):
    gsheet = gsheet.get_all_records()
    df = pd.DataFrame.from_dict(gsheet)

    return df


sheet_url = st.secrets["private_gsheets_url"]

st.cache(ttl=660)
sheet = getgsheet(sheet_url, 0)
file = gsheet2df(sheet)

total_films = len(file)
highest_score = file['Score'].max()
highest_rated_film = file.loc[file['Score'] == highest_score, 'Name'].values.tolist()

highest_rewatchability = file['Rewatchability'].max()
highest_rewatchable_film = file.loc[file['Rewatchability'] == highest_rewatchability, 'Name'].values.tolist()

all_genre = ['Drama', 'Action', 'Horror', 'Comedy', 'Thriller', 'Sci-fi', 'Romance', 'Western', 'Crime', 'Adventure',
             'Fantasy', 'Historical', 'War', 'Noir', 'Mystery', 'Gangster', 'Psychological Thriller', 'Rom Com',
             'Superhero']
genre = list(sorted(set(filter(None, all_genre))))
sub_genre = list(sorted(set(filter(None, all_genre))))
sub_genre.append('N/A')

st.set_page_config(
     layout="wide",
     initial_sidebar_state="expanded",
)

st.markdown(
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css" integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2" crossorigin="anonymous">',
    unsafe_allow_html=True,
)

with st.form(key='Submit Films'):
    with st.sidebar:
        st.sidebar.markdown("## Submit Films")
        Name = st.sidebar.text_input("Film Name", key="Name")
        Genre = st.sidebar.selectbox('Genre', genre)
        Sub_Genre = st.sidebar.selectbox('Sub-Genre', sub_genre)
        Score = st.sidebar.number_input("Score", key="Score", min_value=0.0, max_value=10.0, step=0.5)
        Director = st.sidebar.text_input('Director', key='Director')
        Rewatchability = st.sidebar.number_input("Rewatchability", key="Rewatchability",
                                                 min_value=0.0, max_value=5.0, step=0.5)
        Comment = st.sidebar.text_input("Comment", key="Comment")
        ShortFilm = st.sidebar.radio('Short Film?', ('N', 'Y'))
        submit_button = st.form_submit_button(label='Submit')

if submit_button:
    if Sub_Genre == 'N/A':
        info = [Name, Genre, '', Score, Director, ShortFilm, Rewatchability, Comment]
    else:
        info = [Name, Genre, Sub_Genre, Score, Director, ShortFilm, Rewatchability, Comment]

    if Name in file['Name'].unique():
        st.write('You are updating the record')
        cell = sheet.find(Name)
        sheet.update_cell(cell.row, 4, Score)
        sheet.update_cell(cell.row, 7, Rewatchability)
        file = gsheet2df(sheet)
    else:
        sheet.append_row(info)
        file = gsheet2df(sheet)

st.title('Analysing Films Watched by Jojo')

comments = file[['Name', 'Comment']]
comments['Comment'].replace('', np.nan, inplace=True)
comments.dropna(subset=["Comment"], inplace=True)
comments_to_display = comments.sample().values.tolist()[0]
st.info(f"The comment for {comments_to_display[0]} is {comments_to_display[1]}")

col1, col2 = st.columns(2)

with col1:
    file_col1 = pd.melt(file, id_vars='Name', value_vars=['Genre', 'Sub-Genre'])
    file_col1['value'].replace('', np.nan, inplace=True)
    file_col1.dropna(subset=["value"], inplace=True)

    most_watched_genre = file_col1['value'].value_counts().index.tolist()[0]
    no_most_watched_genre = file_col1['value'].value_counts().values.tolist()[0]

    st.subheader("Number of Films Watched per Genre")
    st.markdown(f"So far, the most watched genre is {most_watched_genre} with "
                f"{no_most_watched_genre} {most_watched_genre} films out of a total of {total_films} watched.")

    st.vega_lite_chart(file_col1, {
            'height': 400,
            "mark": {"type": "arc", "innerRadius": 50},
            "encoding": {
                "theta": {"aggregate": "count", "title": "No. of Films"},
                "color": {
                    "field": "value",
                    "type": "nominal",
                    "scale": {"scheme": "tableau20"},
                    "legend": {"title": "Genre"}
                },
                "tooltip": [
                    {"field": "value", "title": "Genre"},
                    {"aggregate": "count", "title": "No.of Films", "field": "value"}
                ],
            },
            "view": {"stroke": None}
        }, use_container_width=True)

with col2:
    most_watched_genre_df = file_col1[file_col1['value'] == most_watched_genre]
    all_score = file[['Name', 'Score']]
    all_genre_score = pd.merge(most_watched_genre_df, all_score, on='Name')
    rating_of_most_watched_genre = np.average(all_genre_score['Score'])

    top5_genre = file_col1['value'].value_counts()[:5].index.tolist()
    file_col2_1 = file_col1[file_col1['value'].isin(top5_genre)]
    file_col2_2 = file[['Name', 'Score']]
    file_col2 = pd.merge(file_col2_1, file_col2_2, on='Name')

    avg_score_per_genre = file_col2.groupby(['value'], as_index=False).mean()
    highest_avg_score_genre_score = avg_score_per_genre['Score'].max()
    highest_avg_score_genre = avg_score_per_genre[avg_score_per_genre['Score']
                                                  == highest_avg_score_genre_score].values.tolist()[0][0]

    st.subheader("Average Score of Top Five Genres")
    st.markdown(f"The average score of the most watched genre, {most_watched_genre}, is "
                f"{round(rating_of_most_watched_genre, 2)}. Whereas the genre with the highest "
                f"average score is {highest_avg_score_genre} with an average score of "
                f"{np.round(highest_avg_score_genre_score, 2)}.")

    st.vega_lite_chart(file_col2, {
        'width': 'container',
        'height': 400,
        "mark": {"type": "bar"},
        "encoding": {
            "y": {"field": "value",
                  "sort": "-x",
                  "title": None},
            "x": {"aggregate": "mean",
                  "field": "Score",
                  "title": "Average Score",
                  "type": "quantitative"},
            "color": {
                "field": "value",
                "type": "nominal",
                "scale": {"scheme": "tableau20"},
                "legend": {"title": "Genre"}
            },
            "tooltip": [
                {"aggregate": "mean", "title": "Average Score", "field": "Score", "format": ".2f"},
                {"aggregate": "count", "title": "No.of Films", "field": "value"}
            ],
        },

        "view": {"stroke": None}
    }, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    top10_director = file['Director'].value_counts()[:10].index.tolist()
    top10_director_df = file[file['Director'].isin(top10_director)]
    top10_director_df['Director'].replace('', np.nan, inplace=True)
    top10_director_df.dropna(subset=["Director"], inplace=True)

    most_watched_director = top10_director_df['Director'].value_counts().index.tolist()[0]
    no_most_watched_director = top10_director_df['Director'].value_counts().values.tolist()[0]

    st.subheader("Number of Films Watched per Top Ten Director")
    st.markdown(f"So far, the most watched Director is {most_watched_director} with "
                f"{no_most_watched_director} films out of a total of {total_films} watched.")

    st.vega_lite_chart(top10_director_df, {
        'height': 400,
        "mark": {"type": "arc", "innerRadius": 50},
        "encoding": {
            "theta": {"aggregate": "count", "title": "No. of Films"},
            "color": {
                "field": "Director",
                "type": "nominal",
                "scale": {"scheme": "tableau20"},
                "legend": {"title": "Director"}
            },
            "tooltip": [
                {"field": "Director", "title": "Director"},
                {"aggregate": "count", "title": "No.of Films", "field": "value"}
            ],
        },
        "view": {"stroke": None}
    }, use_container_width=True)

with col4:
    avg_score_per_director = top10_director_df.groupby(['Director'], as_index=False).mean()
    highest_avg_score_director_score = avg_score_per_director['Score'].max()
    highest_avg_score_director = avg_score_per_director[avg_score_per_director['Score']
                                                        == highest_avg_score_director_score].values.tolist()[0][0]

    st.subheader("Average Score of Top Ten Directors")
    st.markdown(f"The average score of the most watched Director, {highest_avg_score_director}, is "
                f"{round(highest_avg_score_director_score, 2)}.")

    st.vega_lite_chart(top10_director_df, {
        'height': 400,
        "mark": {"type": "bar"},
        "encoding": {
            "y": {"field": "Director",
                  "sort": "-x",
                  "title": None},
            "x": {"aggregate": "mean",
                  "field": "Score",
                  "title": "Average Score",
                  "type": "quantitative"},
            "color": {
                "field": "Director",
                "type": "nominal",
                "scale": {"scheme": "tableau20"},
                "legend": {"title": "Director"}
            },
            "tooltip": [
                {"aggregate": "mean", "title": "Average Score", "field": "Score", "format": ".2f"},
                {"aggregate": "count", "title": "No.of Films", "field": "value"}
            ],
        },

        "view": {"stroke": None}
    }, use_container_width=True)

st.subheader("Film Ratings for All Time")
st.markdown(f'The highest rated film so far is {highest_rated_film[0]}.')

select_score = st.radio('Sort by:', ('Alphabetical', 'Score'), key='Score')

if select_score == 'Score':
    st.vega_lite_chart(file, {
            "width": "container",
            "mark": {"type": "bar", "cornerRadiusEnd": 4, "tooltip": {"content": "encoding"}},
            "encoding": {
                "x": {"field": "Score",
                      "type": "quantitative",
                      "title": "Score"},
                "y": {"field": "Name",
                      "sort": "-x",
                      "title": None},
                "color": {"field": "Genre",
                          "scale": {"scheme": "tableau20"}}
            },
            "config": {"view": {"stroke": "transparent"}, "axis": {"domainWidth": 1}}
        }, use_container_width=True)
else:
    st.vega_lite_chart(file, {
        "width": "container",
        "mark": {"type": "bar", "cornerRadiusEnd": 4, "tooltip": {"content": "encoding"}},
        "encoding": {
            "x": {"field": "Score",
                  "type": "quantitative",
                  "title": "Score"},
            "y": {"field": "Name",
                  "title": None},
            "color": {"field": "Genre",
                      "scale": {"scheme": "tableau20"}}
        },
        "config": {"view": {"stroke": "transparent"}, "axis": {"domainWidth": 1}}
    }, use_container_width=True)

st.subheader("Rewatchability Score for All Time")
st.markdown(f'The highest rewatchable film so far is {highest_rewatchable_film[0]}.')

select_rewatchable = st.radio('Sort by:', ('Alphabetical', 'Score'), key='Rewatchability')

if select_rewatchable == 'Score':
    st.vega_lite_chart(file, {
            "width": "container",
            "mark": {"type": "bar", "cornerRadiusEnd": 4, "tooltip": {"content": "encoding"}},
            "encoding": {
                "x": {"field": "Rewatchability",
                      "type": "quantitative",
                      "title": "Score"},
                "y": {"field": "Name",
                      "sort": "-x",
                      "title": None},
                "color": {"field": "Genre",
                          "scale": {"scheme": "tableau20"}}
            },
            "config": {"view": {"stroke": "transparent"}, "axis": {"domainWidth": 1}}
        }, use_container_width=True)
else:
    st.vega_lite_chart(file, {
        "width": "container",
        "mark": {"type": "bar", "cornerRadiusEnd": 4, "tooltip": {"content": "encoding"}},
        "encoding": {
            "x": {"field": "Rewatchability",
                  "type": "quantitative",
                  "title": "Score"},
            "y": {"field": "Name",
                  "title": None},
            "color": {"field": "Genre",
                      "scale": {"scheme": "tableau20"}}
        },
        "config": {"view": {"stroke": "transparent"}, "axis": {"domainWidth": 1}}
    }, use_container_width=True)
