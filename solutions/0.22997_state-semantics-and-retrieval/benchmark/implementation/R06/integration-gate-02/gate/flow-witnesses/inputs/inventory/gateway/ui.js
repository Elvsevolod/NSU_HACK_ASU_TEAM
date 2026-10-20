new Vue({data:{products:[]},methods:{
      listProducts(){var vm=this;$.ajax({url:"/inventory",type:"GET",success:function(data){vm.products=data;}});},
      reserveProduct(item){$.ajax({url:"/inventory/reserve",type:"POST",contentType:"application/json",data:JSON.stringify({id:item.id,revision:item.revision})});}}});