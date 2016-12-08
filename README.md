# Item-Catalog
by Fernanda Castillo

## Overview

The item catalog is a project for my Full Stack Course

This project implements a web application and JSON for a list of projects grouped into a category. Users can edit or delete projects if they are the creators. to add, edit or delete a project or category a Google+ third-party authorization is required.

## Instrucitons to Run Project

### To get the project ready
1. Install [**VirtualBox**](https://www.virtualbox.org/)
2. Install [**Vagrant**](https://www.vagrantup.com/)
3. Clone the repository to your local machine.

### Setup the Database & Start the Server
1. Find the repository with the terminal and once inside the catalog use the command $ vagrant up
2. The vagrant machine will install.
3. Once it's complete, type $ vagrant ssh to login to the VM
4. Once in the vm, cd /vagrant will take you to the location of the application
5. type "pyhon setup_catalog_db.py" to create the database
6. type "python application.py" to start the server.

### Open in a webpage
To run the app go to:
    http://localhost:8000
