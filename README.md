# Charity-Donation Web Application

**Team Members:** Shahzaib Zia (24L-3057), Abdullah Tahir, Eman Fatima (24L-3008)

---

A web-based Donation & Charity Management System designed to handle philanthropic operations through a structured relational database model. The system bridges the gap between individual donors, non-governmental organizations (NGOs), and tracking fund deployments to ensure operational transparency.

## System Roles

* **Donors:** Browse ongoing humanitarian campaigns, contribute funds, view transaction history, and access automated receipts.
* **NGOs:** Register organizations, launch specific charitable campaigns, establish goals, and update campaign lifecycles.
* **Administrators:** Maintain platform integrity by overseeing system-wide operations, monitoring donor metrics, and tracking fund allocations.

## Core Features

* **Campaign Management & Progress Tracking:** Active tracking of crowd-funding goals against current collections.
* **Transaction Processing:** Securely logs every donation with explicit payment method tracking and automated donor receipt generation.
* **Fund Allocation Monitoring:** Tracks the actual utilization of resources by mapping campaign collections directly to specific beneficiaries.
* **Data Analytics & Search:** Includes administrative features to filter donors by name, view donation history logs, and pinpoint top financial contributors.

## Relational Database Schema

The core backend architecture utilizes a relational database structure designed around six primary entities to maintain transactional integrity:

* `Donor`: Manages profile credentials, contact records, and registration timelines.
* `NGO`: Tracks verified organization data, official registration numbers, and locations.
* `Campaign`: Holds operational details for fundraising initiatives, linked directly to the hosting NGO.
* `Donation`: Acts as the main transactional bridge recording specific amounts, timestamps, and payment types.
* `Beneficiary`: Categorizes the target recipients or communities receiving programmatic support.
* `Fund Allocation`: Records data on distributed funds to ensure explicit financial tracking per project.

## Tech Stack

* **Frontend:** HTML5, CSS3, JavaScript
* **Database:** SQL / Relational Database System
* **Deployment:** Render
