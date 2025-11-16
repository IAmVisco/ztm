# ZTM - Warsaw public transport schedule API server
## A small server for a miniature home departure board

Forked from [@peetereczek](https://github.com/peetereczek)
#### Description
The client will give you information about departure times for bus/trams using [Warsaw Open Data](https://api.um.warszawa.pl/) API.

To access the data, you need an `api_key` that is provided after creating an account at [Otwarte dane po warszawsku](https://api.um.warszawa.pl/) -> Logowanie -> Rejestracja konta.

The server is a single endpoint `/schedule/:stop_id/:stop_number?lines=1,2,3`.

You can obtain `stop_id` and `stop_number` by searching for a stop at [ZTM](https://www.wtp.waw.pl/rozklady-jazdy/) website. 
In the url `wtp_st` param is the `stop_id` and `wtp_pt` param is `stop_number` (example stop: [Centrum 01](https://www.wtp.waw.pl/rozklady-jazdy/?wtp_dt=2020-01-30&wtp_md=5&wtp_ln=501&wtp_st=7013&wtp_pt=01&wtp_dr=B&wtp_vr=0&wtp_lm=1)).


The public data is coming from [Miasto Stołeczne Warszawa](http://api.um.warszawa.pl ). 
