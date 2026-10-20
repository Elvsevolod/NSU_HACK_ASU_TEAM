class Item {public String id="known";}class Box<T> {public T payload;}
  class Api {@GetMapping("/item") Box item(){Box result=new Box();result.payload=new Item();return result;}}