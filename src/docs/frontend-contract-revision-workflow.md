# Frontend Contract Revision Workflow

```mermaid
flowchart TD
    A[Frontend visits /me] --> B[Read contract info from product data in /me response]
    B --> C{contract.has_revision?}

    C -- false --> D[GET /products/id/contracts/contract_id]
    C -- true --> E[GET /products/id/contracts/contract_id/revision]

    D --> F[Use returned contract details in CMS UI]
    E --> F

    F --> G[User edits contract]
    G --> H[PATCH contract.revision_url]
    H --> I[Contract revision updated]

    E --> O[Read staged distributions from contract.distributions]
    O --> P[Use distribution ids with /products/id/contracts/contract_id/revision/distributions/distribution_id]

    I --> G
    I --> M[DELETE contract.revision_url]
    M --> N[Contract revision discarded]

    I --> J[User publishes contract revision]
    J --> K[POST /products/id/contracts/contract_id/revision/publish]
    K --> L[Live contract updated]
```

When the frontend loads the explicit contract revision endpoint, the response includes the staged
`distributions` collection. Use the returned distribution ids with the parent revision namespace
under
`/products/{product_id}/contracts/{contract_id}/revision/distributions/{distribution_id}` for
child draft detail and mutation. Live distribution detail responses keep using
`/products/{product_id}/contracts/{contract_id}/distributions/{distribution_id}` and expose
`has_revision` plus `revision_url` when a staged draft exists.
