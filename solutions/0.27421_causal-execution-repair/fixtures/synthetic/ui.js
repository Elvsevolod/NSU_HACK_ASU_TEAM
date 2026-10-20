function createBooking(){$.ajax({url:"/bookings",type:"POST",contentType:"application/json",data:JSON.stringify({id:$("#id").val(),title:$("#title").val(),enabled:$("#enabled").is(":checked")})});}
function listBookings(){$.ajax({url:"/bookings",type:"GET"});}
function inspectBooking(){$.ajax({url:"/bookings/"+$("#bookingId").val(),type:"GET"});}
function cancelBooking(){$.ajax({url:"/bookings/"+$("#bookingId").val(),type:"DELETE"});}