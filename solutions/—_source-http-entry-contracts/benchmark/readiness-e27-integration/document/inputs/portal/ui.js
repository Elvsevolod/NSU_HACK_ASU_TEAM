new Vue({data:{documents:[]},methods:{
      listDocuments(){var vm=this;$.ajax({url:"/library",type:"GET",success:function(data){vm.documents=data;}});},
      approveDocument(item){var input={id:item.id,revision:item.revision,approved:true};
       $.ajax({url:"/library/approve",type:"POST",contentType:"application/json",data:JSON.stringify(input)});}
      }});