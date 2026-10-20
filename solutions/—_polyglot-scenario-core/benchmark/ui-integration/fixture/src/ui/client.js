function createArtifact(){
 $.ajax({url:"/artifacts",type:"POST",contentType:"application/json",
  data:JSON.stringify({title:$("#title").val(),quantity:parseInt($("#quantity").val(),10)}),
  success:function(result){sessionStorage.setItem("created",JSON.stringify(result));}});
}
function readArtifact(){
 var saved=JSON.parse(sessionStorage.getItem("created"));
 $.ajax({url:"/artifacts/"+saved.id,type:"GET",success:function(item){$("#quantity_out").text(item.quantity);}});
}
