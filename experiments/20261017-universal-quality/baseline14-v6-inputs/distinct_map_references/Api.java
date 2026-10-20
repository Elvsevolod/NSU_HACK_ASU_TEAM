import java.util.*;class Api {String entry(){Map left=new HashMap();Map right=new HashMap();
    if(left==right){return same();}return different();}
    String same(){return "same";}String different(){return "different";}}