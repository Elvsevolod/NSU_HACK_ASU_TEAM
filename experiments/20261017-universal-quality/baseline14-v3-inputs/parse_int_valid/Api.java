class Api {String entry(){try{Integer.parseInt("12");return after();}
        catch(NumberFormatException failure){return invalid();}}
        String after(){return "after";}String invalid(){return "invalid";}}