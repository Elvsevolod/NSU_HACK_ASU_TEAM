function login(){$.ajax({type:"POST",url:"/login",contentType:"application/json",
 data:JSON.stringify({name:$("#name").val(),password:$("#password").val()}),
 success:function(data){sessionStorage.setItem("login_token",data.token);},
 error:function(){sessionStorage.removeItem("login_token");}});}
 function read(){$.ajax({type:"GET",url:"/protected",headers:{Authorization:"Bearer "+sessionStorage.getItem("login_token")}});}