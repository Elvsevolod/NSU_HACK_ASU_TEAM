interface Worker {String run();}
 class PremiumWorker implements Worker {public String run(){return "premium";}}
 class BasicWorker implements Worker {public String run(){return "basic";}}
 class Start {String entry(){Worker worker=new PremiumWorker();return worker.run();}}