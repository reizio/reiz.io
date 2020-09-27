# reiz.io - Syntactic Source Code Search

Playground: [search.tree.science](https://search.tree.science)

```

            reiz.io architecture (ALPHA)
--------------------------------------------------
input[QUERY]  ->  reiz.reizql.parser[ReizQLAST]  -> |
 user input      intermediate representation        |
                                                    |
                                                    |
reiz.fetch  <-  reiz.reizql.compiler[EdgeQLAST]  <- |
 executor              IR to EdgeQL
   |
   |
   |-------------------------------------------------------------
                                                                |
reiz.samplers[PyPI]   ---|                                      |                  
                         |                                      |
reiz.samplers[GitHub] ---| -> reiz.pipes.cleaner -> |           |
                         |                          |           |
reiz.samplers[....]   ---|                          |           |
 raw source data sampler         sanitizer          |           |
 Python 2 / 3, Markdown,     only Python 3 source   |           |
 videos, various assets.           files            |           |
                                                    |           |
                                                    |           |
    reiz.pipes.insert              <-               |           |
      AST to EdgeQL                                             |
          |                                                     |
          |                                                     |
          |                                                     |
          |        ->        EdgeDB        <-         <-        |
          |                  !core!
          | 
          |
          |
    reiz.db.reset  <-  static/Python-reiz.edgeql <- |
      migration                                     |
       center                                       |
                                                    |
                                                    |
static/Python-reiz.asdl                             |
       |                                            |
       | -> reiz.db.schema -> reiz.db.schema_gen -> |
              schema cfg           ASDL to SDL
                                    compiler
```
