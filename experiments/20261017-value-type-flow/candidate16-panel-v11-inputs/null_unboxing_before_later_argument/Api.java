class Api{String entry(){try{Integer value=null;consume(value,side());return after();}
  catch(NullPointerException failure){return failed();}}void consume(int value,int later){}
  int side(){return 1;}String after(){return "wrong";}String failed(){return "caught";}}