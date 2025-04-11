# SPLIT/r

## Video Demo

Watch on YouTube: [CS50 Final Project: Splitr](https://youtu.be/C74azfNDNIk)

## Description

**Split/r** is a web application designed to simplify the process of sharing expenses among friends. Built using Python, SQL, and JavaScript, it allows users to:

- Register and log in securely.
- Create groups with friends for shared expenses.
- Add and manage expenses within these groups.
- View a dashboard displaying total amounts owed and other relevant statistics.

The application emphasizes user-friendly interfaces and real-time updates to ensure a seamless experience.

## Features

- **User Authentication**: Secure registration and login functionality.
- **Expense Tracking**: Add expenses with descriptions, amounts, and assign them to specific groups.
- **Dashboard Overview**: Visual display of totals, some stats, and tips.
- **Friend-to-Friend Transactions**: Track one-on-one expenses outside of groups.
- **Activity Log**: A history of all transactions across the app.


## How to Run

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Sumitbhamare/splitr.git
   cd splitr
   ```

2. **Create a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```

5. Access the app: Open `127.0.0.1:5000` in your browser.

## Design Choices

- **Index Page**: 
The Dashboard view has been kept minimal, with just the total amount owed / is owed to the user.
Most navigation occurs using the menu bar at the top, specifically, `Groups` and `Friends`. 
Earlier, instead of navigation menus for these, both Sections were on the Dashboard. However, it soon
becomes tedious to scroll through the Dashboard the more these sections get populated. Going with a 
clean and minimal UI for the homepage was an easy decision once these sections were shifted to 
their individual pages.

- **Reused templates**:
The basic template using Jinja is the `layout.html`. This files is similar to Problem Set 9, Finance,
as most of the elements such as the Navigation bar contain similar elements. 
The database management and page designs for elements in
`Friends` are very similar to those in `Groups`, with a few modifications. The `Groups` philosophy was designed
first, and the `Friends` followed suit, with boolean flags in the respective tables to indicate a friends "group".
Special methods were written within the tables to easily identify friend transactions and expenses. 
The shared html files are:
   - `add_expense.html`: The layout for both sections is similar, consisting of input fields for 
   description, total amount, a drop down for Paid by, and each person's individual share. This file 
   also contains JavaScript for form and functionality. The first script shows a button `Split Evenly`which when clicked 
   triggers the script that splits the total amount by the number of users. If the amount cannot be divided evenly, 
   the first user is assigned the extra pennies by default. The second script is a simple paragraph that 
   updates dynamically as the split shares are added to show the remaining amount. It shows a negative amount if 
   the sum of splits exceeds the total amount. Naturally, numerical validations are built-in.
   - `create_entity.html`: Layout used for creating a new group or adding a new friend (one-on-one).
   - `entity_list.html`: The `Groups` and `Friends` sections showing the cards of the groups the user is in
   or the friends with whom the user has a transaction. 
   - `expense_list.html`: The user can click on a `View` button on each of the above cards. This html controls the layout of
   the transactions occuring within those "groups".

- **Database Management System**
The project makes use of Flask's SQLAlchemy (to not rely on CS50 SQL Library). The approach used here
is called Object-Relational Mapping (ORM), where each table in the database is a class and 
each attribute within the class maps to a column in that table. Just as table relations are defined
while using CREATE in SQL, `db.relationship()` provides a method to connect two tables along the column.
Another benefit of using this ORM is the use of raw SQL queries. When the database is queried this way,
it is safer, cleaner, and easier to read and debuf further. All tables and their methods are defined in 
a separate Python file - `models.py`.


- **Flash messages**
The app uses Flask’s flash() functionality to provide user feedback. Flash messages display 
short popups after actions like registration, login, adding/deleting expenses, or error conditions. 
This ensures users are always informed about the outcome of their actions without needing to navigate elsewhere.


- **Authentication files**
The following files and their respective routes are grouped as authentication files: 
`register.html`, `login.html`, `profile.html`. This is similar to Problem Set 9, Finanace, 
as most of the logical is pretty much the same. The use of this application requires a logged in 
user as the website displays their personal finances. Hence, sessions is also used to keep 
a track of the current user. `profile.html` provides the user with the ability to change their 
password. 


- **Other files**
Other miscellaneous files are explained below:
   - `invite_friend.html`: This file is specific for a group. Provides user with a form 
   including a drop down of users to add to a group. Accessed from within a group.
   - `activity.html`: A simple `GET` method HTML file that shows all transactions the user 
   is involved in, groups or friends.
   - `friend.html` and `group.html`: Used to extend `expense_list.html`. While the basic layout
   has been defined, these files show extra information specific to the `Friends` and `Groups` 
   sections respectively.
   - `style.css`: The application uses a mix of custom styles defined here as well as Bootstrap
   designs wherever applicable. This file has been mostly written using AI.
   - `helper.py`: Reused function decorator definition from Finance, as well as a currency function 
   which can be used to set the currency from `app.py`. Default is USD.
   - All images in `/static/` are my own 😄.


## Further Improvements
There is always scope for continuous improvement and development.
Due to time constraints, these following features were on the vision board, but could not be implemented:
- Delete a group / friendship
- An option to "settle" balances
- A search bar for Groups and Friends page


## Use of AI
I have made use of AI, mostly Chat-GPT, for the ideation phase and in writing boilerplate code. 
Some style and Bootstrap usage has also been delegated to AI code completion. It also helped me 
layout and understand Jinja templating, especially for files like `expense_list.html`. Code troubleshooting 
and debugging using AI resulted in a success rate of ~50%. This was an interesting experience overall.


## Acknowledgement
Thank you to the entire CS50 team for the excellent course, amazing hands-on experience and tutoring, 
and the wonderful opportunity!
