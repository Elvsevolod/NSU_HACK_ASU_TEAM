import java.util.*;import org.springframework.web.client.*;
      import org.springframework.http.*;import org.springframework.core.ParameterizedTypeReference;
      class Gateway {RestTemplate client;
        @PostMapping("/bookings") Object createBooking(@RequestBody BookingInput input){try{
          return client.postForObject("http://warehouse/reservations",new HttpEntity(input),Booking.class);
        }catch(RestClientException e){return failed();}}
        String failed(){return "refused";}
        @GetMapping("/bookings") List<Booking> listBookings(){return client.exchange(
          "http://warehouse/reservations",HttpMethod.GET,null,new ParameterizedTypeReference<List<Booking>>(){}).getBody();}
        @GetMapping("/bookings/{bookingId}") Booking inspectBooking(@PathVariable String bookingId){
          return client.getForObject("http://warehouse/reservations/"+bookingId,Booking.class);}
        @DeleteMapping("/bookings/{bookingId}") void cancelBooking(@PathVariable String bookingId){
          client.exchange("http://warehouse/reservations/"+bookingId,HttpMethod.DELETE,null,String.class);}
      }