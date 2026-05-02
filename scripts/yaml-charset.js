'use strict';

hexo.extend.filter.register('server_middleware', function(app) {
  app.use((req, res, next) => {
    if (/\.ya?ml(?:[?#].*)?$/i.test(req.url)) {
      res.setHeader('Content-Type', 'text/yaml; charset=utf-8');
    }
    next();
  });
}, 1);
