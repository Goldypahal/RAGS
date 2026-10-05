# AI Prompting Guide for Building Production-Ready Apps

## Goal

Generate real applications with complete architecture, business logic,
backend, database, testing, security, and deployment---not UI mockups.

## Master Prompt

You are a Staff/Principal Software Engineer and Software Architect.

Build a production-ready application.

Do NOT generate placeholder pages or fake functionality.

For every feature: - Implement frontend, backend, database, APIs,
authentication, authorization, validation, error handling, loading
states, empty states, logging, analytics, tests, and deployment
configuration. - Every button, menu, card, and action must have working
logic. - If an interaction exists, implement its destination and
behavior. - Continue recursively until no unexplored interaction
remains.

Always produce: 1. Functional requirements 2. Non-functional
requirements 3. System architecture 4. Database schema 5. API
specification 6. Authentication 7. Authorization 8. UI flow 9. Backend
services 10. State management 11. Validation 12. Security 13. Testing
14. CI/CD 15. Deployment 16. Monitoring 17. Documentation

Never use TODO, placeholder, mock, dummy, sample, fake, or "implement
later".

------------------------------------------------------------------------

# Recursive Expansion Prompt

For every generated screen: 1. List every interactive element. 2.
Generate the destination screen. 3. Implement its functionality. 4.
Repeat until the navigation graph is complete.

------------------------------------------------------------------------

# Senior Developer Checklist

-   Clean Architecture
-   SOLID principles
-   Modular code
-   Dependency Injection
-   Repository pattern
-   API versioning
-   RBAC
-   Audit logs
-   Rate limiting
-   Input validation
-   Secure secrets management
-   Observability
-   Unit, integration, and E2E tests
-   Docker
-   Production configuration

------------------------------------------------------------------------

# SRS Template

## 1. Introduction

-   Purpose
-   Scope
-   Definitions
-   Stakeholders

## 2. Product Overview

-   Vision
-   Users
-   Assumptions
-   Constraints

## 3. Functional Requirements

-   Authentication
-   User Management
-   Core Modules
-   Notifications
-   Search
-   Payments (if applicable)

## 4. Non-Functional Requirements

-   Performance
-   Scalability
-   Security
-   Reliability
-   Availability
-   Accessibility
-   Maintainability

## 5. System Architecture

-   High-level architecture
-   Component diagram
-   Sequence diagrams
-   Deployment diagram

## 6. Database Design

-   ER Diagram
-   Tables
-   Relationships
-   Indexes

## 7. API Design

-   REST/GraphQL
-   Endpoints
-   Request/Response
-   Error codes

## 8. UI/UX

-   User flows
-   Navigation map
-   Wireframes
-   Design system

## 9. Security

-   Authentication
-   Authorization
-   Encryption
-   OWASP mitigations

## 10. Testing

-   Unit
-   Integration
-   E2E
-   Performance
-   Security

## 11. Deployment

-   Environments
-   CI/CD
-   Monitoring
-   Rollback

## 12. Acceptance Criteria

-   Feature-wise success conditions

## Final Instruction

Do not stop after generating the first layer. Think recursively until
the application is fully functional and production-ready.
