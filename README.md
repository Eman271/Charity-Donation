# Charity-Donation Web Application

**Team Members:** Eman Fatima (24L-3008), Shahzaib Zia (24L-3057), Abdullah Tahir (24L-3061)[cite: 2]

---

A web-based Donation & Charity Management System designed to handle philanthropic operations through a structured relational database model[cite: 2]. The system bridges the gap between individual donors, non-governmental organizations (NGOs), and tracking fund deployments to ensure operational transparency[cite: 2].

## System Roles

* **Donors:** Browse ongoing humanitarian campaigns, contribute funds, view transaction history, and access automated receipts[cite: 2].
* **NGOs:** Register organizations, launch specific charitable campaigns, establish goals, and update campaign lifecycles[cite: 2].
* **Administrators:** Maintain platform integrity by overseeing system-wide operations, monitoring donor metrics, and tracking fund allocations[cite: 2].

## Core Features

* **Campaign Management & Progress Tracking:** Active tracking of crowd-funding goals against current collections[cite: 2].
* **Transaction Processing:** Securely logs every donation with explicit payment method tracking and automated donor receipt generation[cite: 2].
* **Fund Allocation Monitoring:** Tracks the actual utilization of resources by mapping campaign collections directly to specific beneficiaries[cite: 2].
* **Data Analytics & Search:** Includes administrative features to filter donors by name, view donation history logs, and pinpoint top financial contributors[cite: 2].

## Relational Database Schema

The core backend architecture utilizes a relational database structure designed around six primary entities to maintain transactional integrity[cite: 2]:

* `Donor`: Manages profile credentials, contact records, and registration timelines[cite: 2].
* `NGO`: Tracks verified organization data, official registration numbers, and locations[cite: 2].
* `Campaign`: Holds operational details for fundraising initiatives, linked directly to the hosting NGO[cite: 2].
* `Donation`: Acts as the main transactional bridge recording specific amounts, timestamps, and payment types[cite: 2].
* `Beneficiary`: Categorizes the target recipients or communities receiving programmatic support[cite: 2].
* `Fund Allocation`: Records data on distributed funds to ensure explicit financial tracking per project[cite: 2].

## Tech Stack

* **Frontend:** HTML5, CSS3, JavaScript
* **Database:** SQL / Relational Database System[cite: 2]
* **Deployment:** Render
