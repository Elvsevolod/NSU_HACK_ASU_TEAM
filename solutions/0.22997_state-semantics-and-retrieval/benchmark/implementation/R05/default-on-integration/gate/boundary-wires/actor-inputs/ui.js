angular.module("app",[]).controller("Session",function($scope,$http){
 $scope.login=function(){$http({method:"POST",url:"/login",data:{username:$("#username").val(),password:$("#password").val()}})
 .success(function(data,status){if(status==200 && data.name){sessionStorage.setItem("login_token",data.token);}})
 .error(function(failure){sessionStorage.removeItem("login_token");});};
 $scope.read=function(){$http({method:"GET",url:"/protected",headers:{Authorization:"Bearer "+sessionStorage.getItem("login_token")}});};
});