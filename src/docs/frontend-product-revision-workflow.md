# Frontend Product Revision Workflow

```mermaid
flowchart TD
    A[Frontend visits /me] --> B[Read product info from /me response]
    B --> C{has_revision?}

    C -- false --> D[GET /products/id]
    C -- true --> E[GET /products/id/revision]

    D --> F[Use returned product details in CMS UI]
    E --> F

    F --> G[User edits product]
    G --> H[PATCH product.revision_url]
    H --> I[Revision updated]

    E --> O[Read staged services from product.services]
    O --> P[Use service ids with /products/id/revision/services/service_id]

    I --> G
    I --> M[DELETE product.revision_url]
    M --> N[Revision discarded]

    I --> J[User publishes revision]
    J --> K[POST /products/id/revision/publish]
    K --> L[Product updated]
```

When the frontend loads the explicit product revision endpoint, the response includes the staged
`services` collection. Use the returned service ids with the parent revision namespace under
`/products/{product_id}/revision/services/{service_id}` for child draft detail and mutation.
Live service detail responses keep using `/products/{product_id}/services/{service_id}` and expose
`has_revision` plus `revision_url` when a staged draft exists.
