# Design Decisions

## Changelog

2025-09-15: Added Authorization.
2025-09-09: Minor tweaks after finishing up domain layer.
2025-09-03: First draft of this document.

## High level design

### Considerations

- Users should be able to work on a Data Product in stages, i.e. save it and continue working
  on it at a later point in time. Field validation can be performed for each field once it is
  entered, but validation for internal consistency of the whole object can only be done when it
  comes out of draft status.
- The objects we are modelling here are inherently coupled with the objects in
  amsterdam-schema-tools. Some data that lives in the Amsterdam schema are properties
  that need to be available on the Data Product. We can either populate those through the
  types in schema-tools (pure python classes at this point, 2025-09-03), or use the amsterdam-
  schema API which is currently being developed.
- In the near future, further developments will introduce a reviewing process to the workflow.
  This means that specific updates will need to be limited to specific (groups of) people, and
  that more complex validation will be put in place.
- Both validation logic and reviewing logic will cover multiple classes (At least Products
  and Contracts).

### Layers

We come to the following layered application design:

- Presentation (views and (de)serialization)
- Domain (business logic: services + domain model)
- ORM (django models without complex logic)

The **presentation layer** is responsible for:

- Receiving requests
- Validating fields if present
- Serializing responses

For this layer, we will use pydantic to validate and (de)serialize. These pydantic objects are
treated as DTOs (Data Transfer Objects).

The **domain layer** is responsible for:

- Orchestrating use cases
- Complex validation
- Interfacing with amsterdam-schema/schema-tools (although not initially)

This layer has a bunch of domain objects (see below).

The **ORM layer** is responsible for persisting and retrieving stuff to the DB.

Note that this means we do not do validation on this layer (besides the built-in field validation).

### Flow

view -> service -> domain -> repository -> ORM / Django models.

The (domain) service is the interface between the domain and the presentation layer. The
repository is the interface between the domain and the ORM.

### Advantages and drawbacks

This design keeps logic separated from the presentation and persistence layers, this:

- Makes testing easier
- Enables extending the domain with more complex use cases
- Prevents logic to be distributed among multiple Django models

There are some drawbacks:

- We have similar objects in all three layers and need to do translating between them
- Code is a bit harder to grasp coming from a classical Django/fat models background

## The Domain

The domain is divided into three main parts: Product, Team, and Auth.

### Product Aggregate

The main entity users will encounter is the Product, which can be either a DataProduct or
InformationProduct. Each Product can have multiple Contracts, each containing one or more
distributions. The ProductService is the one entrypoint for interacting with the Product and
its underlying elements, the latter should not be altered directly.

#### Aggregate Root: Product

The aggregate root is the entry point of the Product. Whenever we alter something, we get the
entire product, not one of its underlying objects, alter what is needed (either through the
service or on the Product class itself), validated, and persisted _as a whole_.

#### Entities: Product, DataContract, DataService

These entities are identifiable by their id.

#### Value Objects: Distribution

These are objects that don't receive incoming references and don't need to be stable over time.
Within the domain, they don't need an id.

### Team Aggregate

The Team Aggregate only consists of a Team object at this point (2025-09-03). This may change in
the future.

### Authorization

We create a separate Authorization Service, which performs common authorization checks.
There is an Authorizer class that adds some syntactic sugar on top of this. It is instantiated
once, and this singleton (called `authorize`) contains a set of decorators that can perform the
checks from the service. In other (Team/Product) services, we can then use these decorators
to protect certain operations.

The Authorization service combines information from all existing teams and products,
to determine which product belongs to which team. There is also a global setting
with the name of the scope of admins.

Authorization as a whole is behind a feature flag to ease development. There is a setting
FEATURE_FLAG_USE_AUTH, which is set to True by default.

## User Stories / Use Cases

### Admin Role

List all Data Teams

CRUD /teams - Delete only if there are no active Data Products

### Data Team Member Role

List Products belonging to their team

CRUD /products

CRUD /products/<id>/contracts(/<contract_id>)

CRUD /products/<id>/services(/<service_id>)
