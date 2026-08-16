# XYZ AI School Assistant

## Project Description

XYZ AI School Assistant is a FastAPI-based school assistant system that provides school information and role-based access to student data.

The system supports different user roles such as Student, Parent, Teacher, and Principal.

## Features

- Student timetable
- Parent access to student's timetable
- Student attendance
- Parent access to student's attendance
- Teacher and Principal attendance trend
- School-wide attendance access control
- Class schedule
- Basic AI questions
- IoT information
- Python information
- Role-based authorization
- Health check API

## Technologies Used

- Python
- FastAPI
- Pydantic
- Uvicorn
- REST API
- Role-Based Access Control

## API Endpoint

Main API:

POST `/ask`

Health check:

GET `/health`

## Running the Project

Start the FastAPI server using:

```bash
uvicorn app.main:app --reload