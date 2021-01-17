from reiz.edgeql import EdgeQLSelect, EdgeQLSelector

FETCH_FILES = EdgeQLSelect(
    "Module",
    selections=[
        EdgeQLSelector("filename"),
    ],
)

FETCH_PROJECTS = EdgeQLSelect("project", selections=[EdgeQLSelector("name")])
