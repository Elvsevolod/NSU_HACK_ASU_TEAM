import org.springframework.stereotype.Service;
    import org.springframework.beans.factory.annotation.Autowired;
    @Service class StockWorker {
      @Autowired ReservationStore repository;
      Reservation accept(String key) { Reservation item = new Reservation(key); repository.save(item); return item; }
      Reservation reject(String key) { return null; }
      String status(String key) { return "ready"; }
    }