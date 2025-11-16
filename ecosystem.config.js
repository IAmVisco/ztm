module.exports = {
  apps : [{
    name: 'ztm',
    script: 'gunicorn -b 0.0.0.0:4001 app:app',
    env: {
        ZTM_API_KEY: 'foobar'
    }
  }]
};