DOCUMENTATION
OVERVIEW
thsi project is a flaskbased web application designed to manage patient data calculate stroke risk score , and provide seperate dashboards for users and admins. it integrated muliple databases- SQlight,CouchDB(nonSQL) to handle authentication, feedback, medical records, and patient history.
This system supports:
>Secure registration &Login for users and admins
>Rist analysis based on medical data
>Patient history tracking
>Feedback collection
>Admin tools to manage users medical and reviews

SECURE SOFTWARE PRINCIPLES APPLIES
>Authentication and Session Manatgement:secure login with password Hashing,session traking
>Acess control/Least Privilaged:separate routs for users and admins,role checks prevent unoutherised access
>Input validation
>Fail-safe Defaukts: flashes messages
>Monitoring:Snapshots of pationt data updated


FEATURES
USER FEATURS:
>Registraton&Login:user can register with personal details to register and login
>Dashboard:displays personilized information, like risk and medical data
>Risk analysis:Calculates stroke risk score based on age,BMI,glucose,hypertension,heart diseases
>Feedback:Users can rate thier experiance,and leave a comment, wich is storedin nonSQL Database
>Patient History:users can see thier own medical history
>Profile management:users can update thier personal information.

ADMIN FEATURES

during registration and login users can select opthion 'admin' for admin login
>Admin dashboard:Displayes tootla patients,high risk patient cout, recent entries
>User management: View all registered users,,edit/delete users data(Personal+medical)
>Risk monitoring:analyze patient risk scores,
>view patient portals aswell
>Feedback revie
>Patient history: can see all patient history updated everytime a user updates thier data


USER STORIES
As a USER:
>user can register using personla details, and login using thier email and password, user can see a dashboard when they login, wecan enter our medical details in 'add additional medical details', then user can view analyze my data wich is the user profile and states, showing the risk levels and a few health tips,
users can update thir own data, and give a feedback, and logout

As an ADMIN:
>admin can select the option admin in 'role' while registring and at login, which will take them to admn portal, on the home page we can see an averview of patients statistics.
admin can manage user accounts(edit thier detail, delet them), admin can also see all patients history(any updates done on thier details),
admin can also see all the feedbacks left by patients.
can also monitor patient history records.

DATABASES
used 2 typed of databases, 
>SQLite: for user and admins records
>CouchDB(Non-SQL): for feedbacks and patient history snapshots


TESTING
did UNIT testing and INTEGRITY testing for each feature and also to test combined fuctionality.


And finally i registere a few users and one admin ,based on the dataset given to us.
>Admin credentials
admin@gmail.com
admin
