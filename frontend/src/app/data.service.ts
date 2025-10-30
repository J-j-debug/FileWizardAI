import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class DataService {

  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {
  }

  getFormattedFiles(params: any): Observable<any> {
    return this.http.get<any>(this.apiUrl + "/get_files", { params: params });
  }

  updateStructure(newStructureBody: any): Observable<any> {
    return this.http.post<any>(this.apiUrl + "/update_files", newStructureBody);
  }

  ragSearch(params: HttpParams): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/rag_search`, { params });
  }

  openFile(fileToOpen: any): Observable<any> {
    return this.http.post<any>(this.apiUrl + "/open_file", { file_path: fileToOpen });
  }

  getLLMProviders(): Promise<any> {
    return this.http.get<any>(this.apiUrl + "/llm_providers").toPromise();
  }

  getCurrentLLMConfig(): Promise<any> {
    return this.http.get<any>(this.apiUrl + "/current_llm_config").toPromise();
  }

  updateLLMConfig(configData: any): Promise<any> {
    return this.http.post<any>(this.apiUrl + "/llm_config", configData).toPromise();
  }

  indexFiles(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/index_files`, data);
  }
}
