import java.nio.file.*;
import java.util.*;
import com.github.javaparser.*;
import com.github.javaparser.ast.*;
import com.github.javaparser.ast.body.*;

// Optional extractor comparator only. Target classes are parsed, never loaded.
public class ExtractorProbe {
  public static void main(String[] paths) throws Exception {
    JavaParser parser=new JavaParser(new ParserConfiguration().setLanguageLevel(ParserConfiguration.LanguageLevel.BLEEDING_EDGE));
    for(String path:paths){
      ParseResult<CompilationUnit> result=parser.parse(Paths.get(path));
      if(!result.isSuccessful()){System.err.println("PARSE\t"+path+"\t"+result.getProblems());continue;}
      CompilationUnit unit=result.getResult().get();
      for(CallableDeclaration<?> method:unit.findAll(CallableDeclaration.class)){
        String owner=method.findAncestor(TypeDeclaration.class).map(TypeDeclaration::getNameAsString).orElse("<anonymous>");
        String name=method instanceof ConstructorDeclaration?"<init>":method.getNameAsString();
        List<String> parameters=new ArrayList<>();
        method.getParameters().forEach(p->parameters.add(p.getType().asString().replaceAll("\\s+","")));
        System.out.println(path+"\t"+owner+"\t"+name+"\t"+method.getBegin().get().line+"\t"+String.join(",",parameters));
      }
    }
  }
}
